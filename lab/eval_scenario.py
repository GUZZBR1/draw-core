"""Auditoria por fase do cenário escrever→apagar→redesenhar→mover.

Consome um MP4 do sim_source com bundle GT que declara ``events``,
``stroke_phase`` e ``page_ink_final``, e mede o que cada fase exige do
laço real: a escrita confirma, a região apagada perde pixels
confirmados, o traço redesenhado confirma de novo (o contrato do E3:
pixel apagado não fica provisório para sempre) e a folha movida não
zera o canvas. Cada fotografia usa a âncora que a worker realmente
publicava naquele frame; para cenário simples, sem events, o caminho
é o eval_capture de sempre.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from draw.paper import perspective_matrix  # noqa: E402
from lab import sim_isp  # noqa: E402
from lab.eval_capture import pixel_metrics, run_pipeline  # noqa: E402


def _stroke_mask(shape, points, thickness):
    mask = np.zeros(shape, np.uint8)
    cv2.polylines(mask, [points.astype(np.int32)], False, 255, int(thickness))
    return mask


def _page_expected(bundle, applied_upto, erased):
    """Tinta esperada na folha por fase, na ordem do simulador.

    A borracha correu ANTES do redesenho: ela corta os traços da
    primeira escrita (fase 0), mas o redesenho (fase 1) nasce depois
    dela — um traço de fase 1 dentro do retângulo apagado é tinta
    esperada, não falso positivo. Apagar as duas fases juntas zerava
    o redesenho do gabarito e punia a confirmação correta.
    """
    shape = bundle["page_ink_full"].shape
    expected = np.zeros(shape, np.uint8)
    points, offsets = bundle["points"], bundle["offsets"]
    stroke_phase = bundle["stroke_phase"]

    def _draw(indices):
        for index in indices:
            geo = points[offsets[index] : offsets[index + 1]]
            cv2.polylines(
                expected,
                [geo.astype(np.int32)],
                False,
                255,
                int(bundle["thickness"][index]),
            )

    applied = range(applied_upto)
    _draw(i for i in applied if stroke_phase[i] == 0)
    if erased:
        x, y, w, h = (int(v) for v in bundle["erase_rect"])
        expected[y : y + h, x : x + w] = 0
    _draw(i for i in applied if stroke_phase[i] != 0)
    return expected


def _page_expected_phases(bundle, applied_upto, erased):
    """(fase 0 pós-borracha, fase 1) separadas por era de existência.

    A projeção por registros é por passada: um traço só pode estar
    onde uma passada capaz de vê-lo o depositou. Separar por fase é
    o que permite projetar o redesenho só por registros a partir da
    segunda escrita — projetá-lo por passadas anteriores criava
    verdade fantasma e derrubava o recall medido.
    """
    shape = bundle["page_ink_full"].shape
    mask0 = np.zeros(shape, np.uint8)
    mask1 = np.zeros(shape, np.uint8)
    points, offsets = bundle["points"], bundle["offsets"]
    stroke_phase = bundle["stroke_phase"]
    for index in range(applied_upto):
        geo = points[offsets[index] : offsets[index + 1]]
        target = mask0 if stroke_phase[index] == 0 else mask1
        cv2.polylines(
            target,
            [geo.astype(np.int32)],
            False,
            255,
            int(bundle["thickness"][index]),
        )
    if erased:
        x, y, w, h = (int(v) for v in bundle["erase_rect"])
        mask0[y : y + h, x : x + w] = 0
    return mask0, mask1


def _final_checkpoint(checkpoints, events):
    """O checkpoint do ÚLTIMO evento declarado — nunca um anterior.

    Escolher "o último com IoU" mascarava perda de canvas no fim
    (movimento que tira a folha de cena, ou vídeo truncado): o
    relatório cantava o sucesso de uma fase anterior como estado
    final. Sem checkpoint do evento final, ou com canvas ausente
    nele, as métricas ficam indisponíveis e o status diz por quê.
    """
    terminal_frame = int(events[-1]["end"]) - 1 if events else -1
    final = next((c for c in checkpoints if c["frame"] == terminal_frame), None)
    if final is None:
        return {"status": "sem checkpoint do evento final"}
    if "iou" not in final:
        return {
            "status": f"canvas ausente no evento final ({final.get('status')})",
            "frame": final["frame"],
            "phase": final["phase"],
            "confirmed_px": final.get("confirmed_px"),
            # Sem isto a isencao de ausencia nunca chegava ao verdict
            # — o dict reconstruido dropava a flag e o score_report
            # penalizava o lift_out final como perda de canvas.
            "absence": bool(final.get("absence")),
        }
    return final


def _project(mask, corners, page_to_scene, canvas_hw, scene_map=None):
    """Projeta máscara de página para a grade do canvas pela âncora.

    Com ``scene_map`` (mapa denso cena→página da folha curvada),
    página→cena é remap — a homografia nominal não descreve a dobra.
    """
    height, width = canvas_hw
    destination = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
    matrix = perspective_matrix(np.asarray(corners, np.float32), destination)
    if scene_map is not None:
        scene = cv2.remap(
            mask,
            scene_map[0],
            scene_map[1],
            cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
        )
        return cv2.warpPerspective(
            scene, matrix, (width, height), flags=cv2.INTER_NEAREST
        )
    return cv2.warpPerspective(
        mask, matrix @ page_to_scene, (width, height), flags=cv2.INTER_NEAREST
    )


def _project_via_registrations(
    mask,
    registrations,
    frame,
    *,
    canvas_hw,
    quads=None,
    curl=None,
    page_corners=None,
    min_frame=None,
    curved=False,
):
    """GT na grade do canvas pela cadeia das passadas até `frame`.

    Cada registro de run_pipeline guarda âncora, quad de registro,
    quad submetido e o índice do frame de origem. A evidência da
    passada i ficou em X_i·p da grade, com
        X_i = P(âncora_i)·P(reg_i)⁻¹ · P(sub_i)·H_i
    — a mesma cadeia do evaluate_canvas. A união sobre os registros
    com ``frame <= frame`` descreve o que o canvas confirmado pode
    conter naquele checkpoint: tinta depositada antes de um
    lift/move continua projetando pelo registro da sua passada, não
    pela pose nova (que a colocaria fora da grade). Registros sem
    submetido/frame colapsam P(sub)·H na escala página→grade, como
    no eval_capture. Folha curvada remapa página→cena pelo mapa
    denso sintetizado da pose daquela passada.

    ``min_frame`` restringe a passadas que já podiam ver a máscara:
    traço de fase 1 projetado por registro anterior ao redesenho
    ocupa posição que nenhuma passada depositou — verdade fantasma
    que derruba a métrica de recall do redesenho. ``curved`` marca
    bundle de folha curvada: sem a pose verdadeira do frame o mapa
    plano página→grade mentiria pior que a projeção pelo mapa denso
    do checkpoint — o registro é pulado e, sem nenhum projetável,
    a função cai fora para o fallback do chamador.

    Retorna None quando não há registro utilizável — o chamador cai
    na projeção pela pose do checkpoint, como antes.
    """
    height, width = canvas_hw
    destination = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
    true_quads = None if quads is None else np.asarray(quads, np.float32)
    valid = [
        r
        for r in registrations
        if isinstance(r, dict)
        and (r.get("frame") is None or r["frame"] <= frame)
        and (min_frame is None or r.get("frame") is None or r["frame"] >= min_frame)
    ]
    if not valid:
        return None
    # Dedup por bytes — repetições da mesma geometria projetam igual.
    seen = {}
    for reg in valid:
        key = (
            None
            if reg.get("anchor") is None
            else np.asarray(reg["anchor"], np.float32).tobytes(),
            None
            if reg.get("quad") is None
            else np.asarray(reg["quad"], np.float32).tobytes(),
            None
            if reg.get("submitted") is None
            else np.asarray(reg["submitted"], np.float32).tobytes(),
            reg.get("frame") if true_quads is not None else None,
        )
        seen.setdefault(key, reg)
    page_to_grid = np.diag([width / mask.shape[1], height / mask.shape[0], 1.0])
    if page_corners is None:
        ph, pw = mask.shape
        page_corners = np.float32([[0, 0], [pw, 0], [pw, ph], [0, ph]])
    projections = []
    for reg in seen.values():
        anchor, quad, sub = reg.get("anchor"), reg.get("quad"), reg.get("submitted")
        rframe = reg.get("frame")
        if anchor is None or quad is None:
            reg_matrix = np.eye(3, dtype=np.float64)
        else:
            reg_matrix = perspective_matrix(
                np.asarray(anchor, np.float32), destination
            ) @ np.linalg.inv(
                perspective_matrix(np.asarray(quad, np.float32), destination)
            )
        has_true_pose = (
            sub is not None
            and true_quads is not None
            and rframe is not None
            and 0 <= rframe < len(true_quads)
            and np.asarray(true_quads[rframe]).shape == (4, 2)
            and np.isfinite(true_quads[rframe]).all()
        )
        if curved and not has_true_pose:
            # Folha curvada sem pose por frame (bundle salvo antes
            # de consumir o vídeo): a escala plana página→grade
            # mentiria pior que o mapa denso do checkpoint.
            continue
        if curl is not None and has_true_pose and page_corners is not None:
            scene_map = sim_isp.scene_to_page_map(
                np.linalg.inv(
                    cv2.getPerspectiveTransform(
                        page_corners, np.asarray(true_quads[rframe], np.float32)
                    )
                ),
                mask.shape[1],
                mask.shape[0],
                curl,
            )
            scene = cv2.remap(
                mask,
                scene_map[0],
                scene_map[1],
                cv2.INTER_NEAREST,
                borderMode=cv2.BORDER_CONSTANT,
            )
            chain = reg_matrix @ perspective_matrix(
                np.asarray(sub, np.float32), destination
            )
            projections.append(
                cv2.warpPerspective(
                    scene, chain, (width, height), flags=cv2.INTER_NEAREST
                )
            )
            continue
        if has_true_pose:
            input_map = perspective_matrix(
                np.asarray(sub, np.float32), destination
            ) @ perspective_matrix(
                page_corners, np.asarray(true_quads[rframe], np.float32)
            )
        else:
            input_map = page_to_grid
        projections.append(
            cv2.warpPerspective(
                mask, reg_matrix @ input_map, (width, height), flags=cv2.INTER_NEAREST
            )
        )
    if not projections:
        return None
    if len(projections) == 1:
        return projections[0]
    return np.maximum.reduce(projections)


def _pipeline_summary(pipeline):
    """Resumo JSON-seguro do resultado do run_pipeline.

    ``anchors``/``registrations`` carregam ndarrays — o relatório
    vira JSON, então ficam as contagens (como no main do
    eval_capture). Os registros brutos seguem na variável local do
    audit para projetar o GT pela cadeia das passadas.
    """
    summary = dict(pipeline)
    final_mask = summary.pop("mask", None)
    corners = summary.pop("corners", None)
    anchors = summary.pop("anchors", ()) or ()
    registrations = summary.pop("registrations", []) or []
    summary["final_confirmed_px"] = (
        None if final_mask is None else int((np.asarray(final_mask) > 0).sum())
    )
    summary["anchor_corners"] = None if corners is None else corners.tolist()
    summary["anchor_count"] = len(anchors)
    summary["registration_count"] = len(registrations)
    return summary


def audit(video, gt_path, *, fps=None, models=None, save_masks=None, verify="manifest"):
    # models=() quebrava no .get: dict vazio e não tupla.
    models = models or {}
    with np.load(gt_path, allow_pickle=False) as archive:
        bundle = {key: archive[key] for key in archive.files}
    missing = {"events", "stroke_phase", "stroke_erased", "page_ink_final"} - set(
        bundle
    )
    if missing:
        raise ValueError(
            f"bundle sem campos de cenário {sorted(missing)}; use eval_capture"
        )
    events = json.loads(str(bundle["events"]))
    capture = cv2.VideoCapture(str(video))
    try:
        snapshots = {}
        ends = {phase["end"] - 1: phase for phase in events}

        def on_frame(loop, worker, frame_index):
            if frame_index not in ends:
                return
            snapshots[frame_index] = {
                "confirmed": (
                    None if loop.clean_mask is None else loop.clean_mask.copy()
                ),
                "provisional": (
                    None
                    if loop.clean_provisional_mask is None
                    else loop.clean_provisional_mask.copy()
                ),
                "corners": (None if worker is None else worker.anchor_corners),
            }

        pipeline = run_pipeline(
            capture,
            fps=fps,
            neural_model=models.get("neural"),
            page_clean_model=models.get("page_clean"),
            hand_model=models.get("hand"),
            on_frame=on_frame,
            verify=verify,
        )
    finally:
        capture.release()

    registrations = list(pipeline.get("registrations") or [])
    pipeline = _pipeline_summary(pipeline)
    canvas_hw = tuple(pipeline["canvas_shape"])
    stroke_phase = bundle["stroke_phase"]
    points, offsets = bundle["points"], bundle["offsets"]
    shape = bundle["page_ink_full"].shape

    def phase_stroke_masks(phase_index):
        masks = []
        for index in np.nonzero(stroke_phase == phase_index)[0]:
            geo = points[offsets[index] : offsets[index + 1]]
            masks.append(_stroke_mask(shape, geo, bundle["thickness"][index]))
        return masks

    checkpoints = []
    applied_upto = 0
    erased = False
    writes_seen = 0
    # Geometria por fase: quad_end no evento marca a pose no último
    # frame da fase geométrica (move/lift_out/return). Fases sem gesto
    # herdam a pose do último gesto — move+lift+return juntos ficam
    # corretos, não só "antes/depois de qualquer movimento". Bundles
    # antigos sem quad_end caem na heurística de pose final.
    ph, pw = bundle["page_ink_full"].shape
    page_corners = np.float32([[0, 0], [pw, 0], [pw, ph], [0, ph]])
    quad_now = np.asarray(bundle["quad"], np.float32)
    has_quad_end = any("quad_end" in p for p in events)
    moved = False
    curl = json.loads(str(bundle["page_curl"])) if "page_curl" in bundle else None
    for phase in events:
        frame = phase["end"] - 1
        if phase["kind"] == "write":
            writes_seen += 1
            # fase write termina com a lista dela toda aplicada
            applied_upto = (
                int((stroke_phase == 0).sum())
                if writes_seen == 1
                else int(stroke_phase.size)
            )
        if phase["kind"] == "erase":
            erased = True
        snap = snapshots.get(frame)
        if snap is None:
            continue
        if save_masks is not None and snap["confirmed"] is not None:
            save_masks.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(
                str(save_masks / f"confirmed_{phase['kind']}_{frame}.png"),
                (np.asarray(snap["confirmed"]) > 0).astype(np.uint8) * 255,
            )
        quad_end = phase.get("quad_end")
        if quad_end is not None:
            quad_now = np.asarray(quad_end, np.float32)
            moved = True
        elif phase["kind"] in ("move", "lift_out", "return"):
            # Bundle antigo sem quad_end: só sabemos a pose final.
            moved = True
        if has_quad_end or not moved or "page_to_scene_final" not in bundle:
            page_to_scene = cv2.getPerspectiveTransform(page_corners, quad_now)
        else:
            page_to_scene = bundle["page_to_scene_final"]
        scene_map = None
        if curl is not None:
            scene_map = sim_isp.scene_to_page_map(
                np.linalg.inv(page_to_scene), pw, ph, curl
            )
        elif "scene_to_page_x" in bundle:
            tag = "final_" if moved else ""
            scene_map = (
                bundle[f"scene_to_page_{tag}x"],
                bundle[f"scene_to_page_{tag}y"],
            )
        expected0, expected1 = _page_expected_phases(bundle, applied_upto, erased)
        write_starts = [p["start"] for p in events if p["kind"] == "write"]
        redraw_era = write_starts[1] if len(write_starts) > 1 else None
        curved = curl is not None or "scene_to_page_x" in bundle
        entry = {
            "frame": frame,
            "phase": phase["kind"],
            "phase_start": phase["start"],
        }
        if snap["corners"] is None or snap["confirmed"] is None:
            # lift_out/absent tiram a folha de cena de propósito: sem
            # âncora nessa fase é ausência geometricamente impossível
            # de pontuar, não falha — MAS só quando o canvas persistiu:
            # confirmed=None significa que o laço perdeu a tinta,
            # e perder tinta durante a ausência é falha de verdade.
            absent = (
                phase["kind"] in ("lift_out", "absent")
                and snap["confirmed"] is not None
            )
            entry["status"] = (
                "ausência (folha fora de cena)" if absent else "sem âncora/canvas"
            )
            entry["absence"] = absent
            entry["confirmed_px"] = (
                None
                if snap["confirmed"] is None
                else int((np.asarray(snap["confirmed"]) > 0).sum())
            )
            checkpoints.append(entry)
            continue
        corners = snap["corners"]
        confirmed = np.asarray(snap["confirmed"]) > 0
        provisional = (
            np.zeros_like(confirmed)
            if snap["provisional"] is None
            else np.asarray(snap["provisional"]) > 0
        )

        def project_truth(
            page_mask,
            *,
            min_frame=None,
            frame=frame,
            corners=corners,
            page_to_scene=page_to_scene,
            scene_map=scene_map,
            curved=curved,
        ):
            # Registros das passadas até o frame do checkpoint: a
            # tinta persistida de fases antigas (pré-lift/move) fica
            # onde a cadeia de registro dela a depositou — projetar
            # pela pose do checkpoint deslocaria a verdade para fora
            # da grade e marcaria ausência injusta.
            projected = _project_via_registrations(
                page_mask,
                registrations,
                frame,
                canvas_hw=canvas_hw,
                quads=bundle.get("quads"),
                curl=curl,
                page_corners=page_corners,
                min_frame=min_frame,
                curved=curved,
            )
            if projected is not None:
                return projected > 0
            return _project(page_mask, corners, page_to_scene, canvas_hw, scene_map) > 0

        truth = project_truth(expected0)
        if expected1.any():
            # Redesenho só por passadas a partir da segunda escrita:
            # registros anteriores nunca o viram — projetá-lo por eles
            # criaria verdade fantasma e derrubaria o recall medido.
            truth |= project_truth(expected1, min_frame=redraw_era)
        entry.update(pixel_metrics(confirmed, truth))
        entry["confirmed_px"] = int(confirmed.sum())
        entry["provisional_px"] = int(provisional.sum())
        # Redesenho esperado: só exclui do residual quando a fase 1 já
        # foi aplicada — antes dela, tinta no retângulo é resíduo de
        # verdade mesmo onde um traço futuro vai cair.
        redraw_canvas = np.zeros(confirmed.shape, bool)
        redraw_masks = phase_stroke_masks(1) if writes_seen >= 2 else []
        if redraw_masks:
            redraw = np.zeros(shape, np.uint8)
            for mask in redraw_masks:
                redraw |= mask
            redraw_canvas = project_truth(redraw, min_frame=redraw_era)
            denom = max(1, int(redraw_canvas.sum()))
            entry["redraw_confirmed_recall"] = (
                float((confirmed & redraw_canvas).sum()) / denom
            )
            entry["redraw_provisional_px"] = int((provisional & redraw_canvas).sum())
        x, y, w, h = (int(v) for v in bundle["erase_rect"])
        if w and h:
            rect_mask = np.zeros(shape, np.uint8)
            rect_mask[y : y + h, x : x + w] = 255
            rect_canvas = project_truth(rect_mask)
            # Resíduo = confirmado no retângulo apagado FORA do que o
            # redesenho legítimo cobre — traço de fase 1 dentro do
            # retângulo é tinta esperada, não sobra da borracha.
            residual = confirmed & rect_canvas & ~redraw_canvas
            entry["confirmed_in_erased_px"] = int(residual.sum())
        checkpoints.append(entry)

    final = _final_checkpoint(checkpoints, events)
    report = {
        "video": str(video),
        "checkpoints": checkpoints,
        "pipeline": pipeline,
        "verdict": {
            "status": final.get("status"),
            "absence": bool(final.get("absence")),
            "final_iou": final.get("iou"),
            "final_recall": final.get("recall"),
            "final_confirmed_px": final.get("confirmed_px"),
            "redraw_confirmed_recall": final.get("redraw_confirmed_recall"),
            "redraw_provisional_px": final.get("redraw_provisional_px"),
            "residual_confirmed_in_erased_px": final.get("confirmed_in_erased_px"),
        },
    }
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--gt", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--fps", type=float)
    parser.add_argument("--neural-model")
    parser.add_argument("--page-clean-model")
    parser.add_argument("--hand-model")
    parser.add_argument(
        "--save-masks",
        type=Path,
        help="grava a máscara confirmada de cada checkpoint como PNG",
    )
    args = parser.parse_args(argv)
    report = audit(
        args.video,
        args.gt,
        fps=args.fps,
        models={
            "neural": args.neural_model,
            "page_clean": args.page_clean_model,
            "hand": args.hand_model,
        },
        save_masks=args.save_masks,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
