# Geometric fidelity in the export of paper drawings

## Abstract

Converting a paper drawing into a digital artifact can support editing, documentation, printing, and integration with other tools. Its usefulness depends on which drawing characteristics remain recognizable after export. “Geometric fidelity” is not a single property: position, scale, stroke width, shape, stroke order, and color can matter differently depending on the use. This article proposes a framework for evaluating these dimensions in a camera-assisted drawing system without describing its internal representation or how the file is produced. The framework relates each aspect to a downstream need and an external measure. The protocol compares reference drawings with exported artifacts re-imported into categories of destination tools, using task-specific tolerances defined before analysis. Tables and figures organize aspects, uses, and compatibility as empty categories. Since no experimental results are available, the article makes no claim about achieved accuracy, preservation, or compatibility. The proposal makes explicit what is compared, for which use, and within what limits, avoiding a universal fidelity criterion.

**Keywords:** export; geometric fidelity; drawing; interoperability; evaluation

## 1. Introduction

A paper drawing can be useful beyond the moment it was made. The person may want to edit the composition, keep a record, print a copy, or transfer the content to another tool. The move to a digital artifact raises an evaluation question: which properties must remain for the result to serve each purpose? A visually similar image may lose information relevant to editing; an editable representation may preserve shapes and still alter scale or color when printed.

Geometric fidelity is usually treated as a general property, but it brings together distinct dimensions. The position of elements affects alignment; scale affects physical dimensions and proportions; stroke width affects legibility and appearance; shape affects contour and gesture; stroke order may matter for review; color affects documentation and reproduction. These aspects have different criteria and units of observation. A single global measure can hide small changes in one dimension and serious ones in another.

This article proposes evaluating artifacts exported by a camera-assisted drawing system, without specifying an internal format or representation method. The question is: **which aspects of position, scale, width, shape, order, and color should be compared to judge the usefulness of an export in downstream tasks?** The answer depends on the intended use. For this reason, the proposal does not choose a universal threshold, but requires that tolerances be justified before the results are analyzed.

The article offers three contributions. First, it presents a taxonomy of fidelity aspects and relates each one to editing, documentation, printing, and integration. Second, it defines external measures and comparisons against an independent scan of the original. Third, it proposes re-import tests in categories of tools and a compatibility matrix, without claiming that any tool is supported. The contributions specify how to evaluate and report; they do not demonstrate achieved preservation.

Section 2 reviews vectorization, stroke representation, interoperability, and digital preservation. Section 3 defines the fidelity aspects and their uses. Section 4 describes reference drawings, destination categories, metrics, and tolerances. Section 5 reserves the format for future results. Section 6 discusses possible divergences between uses. Section 7 delimits validity and coverage, and Section 8 concludes by indicating the evidence needed.

The evaluation considers both the artifact in isolation and its behavior in a destination tool. A file may keep an apparent geometry when viewed and change after re-import or printing. The comparison does not assume that viewing, editing, and preservation are equivalent. The protocol records the use category, the conditions of the destination, and the aspect being tested. If interaction with a tool alters the result, that alteration belongs to the evaluation scenario and is not automatically attributed to a specific format or component.

The comparison tolerance is a decision about use. For printing, size and scale may have different requirements from a digital draft; for documentation, color and shape may be essential; for editing, order and logical separation may be relevant. The tolerance is justified by the objective, by an appropriate reference, or by user criteria. The article does not present values without such a basis and keeps the aspects separate so that distinct needs are not compressed into a single judgment.

The topic also involves preservation and future access. An artifact that is useful today may become difficult to open or edit in another context. Geometric evaluation alone does not cover durability, metadata, licensing, or file accessibility, although these topics may be necessary in a complete evaluation. The scope here is the relation between the original drawing and the characteristics preserved in the exported artifact, with attention to re-import and downstream use.


The reference is an evaluation artifact, not a perfect source by definition. The scanning method and lighting conditions can alter color, edges, and scale. When the question includes physical dimensions, the reference must retain that information; when it includes order, the record must follow the execution. The proposal requires each evaluated aspect to have a corresponding source and that gaps be declared.

## 2. Related work

### 2.1 Vectorization and stroke representation

Vectorization converts visual information into representations described by shapes or trajectories, whereas raster images organize samples on a grid. The literature on the vectorization of lines, drawings, and documents discusses contour accuracy, continuity, perceptual simplification, and feature preservation. These works indicate possible measures, such as distance between curves, region overlap, width difference, or order preservation. However, the objectives vary: recognizing text, reconstructing a map, or editing a sketch do not require the same properties.

Research on digital drawing also studies pen trajectories, stroke reconstruction, sketch similarity, and ways of measuring quality. Geometric comparison can use corresponding points, distance between contours, topological structure, or perceptual evaluation. No metric covers position, scale, width, shape, and order at the same time. The choice depends on the question and on the possibility of obtaining an independent reference.

One difficulty is aligning two representations before comparing them. If the page changes orientation or scale, an apparent displacement may reflect the preparation of the reference, not the export. The literature on image registration and shape comparison helps structure this issue, but the procedures used must be declared without inferring internal mechanisms of the system. This article limits the report to the external measures chosen.


Classic works on line-drawing conversion discuss contour recovery, junctions, topology, and geometric reconstruction. More recent studies on stroke and sketch vectorization broaden the focus to curve networks, drawings of variable thickness, and interactive editing [1–16]. These works show that geometry is made up of properties, not of a single distance. A metric that compares contours may not assess stroke order; a junction reconstruction does not measure color. The present article uses these antecedents to select external measures, without evaluating any specific vectorization method.

Image quality assessment offers structural and perceptual measures that compare a reference and a transformed version. The Hausdorff distance emphasizes discrepancies between sets of points; structural indices summarize differences in appearance at different scales [17–19]. These metrics can support certain comparisons, but they do not demonstrate preservation of editable structure or semantics. Research on curve networks in sketches also relates geometric representation to editing and reconstruction possibilities [20]. The selection of a measure must therefore follow the aspect and the use.

### 2.2 Interoperability and destination formats

Interoperability concerns the exchange of content between tools and services. Graphic representation standards and studies of authoring systems document that appearance, editable structure, and semantics can be preserved differently when migrating between applications. A flat image may keep its appearance without allowing stroke-level editing; a structured representation may facilitate alteration and still depend on compatibility at the destination. Export success must thus be evaluated by the downstream task, not merely by the existence of a file.

Conformance and compatibility tests usually observe reading, writing, rendering, and exchange of attributes. For drawings, the relevant set includes shape, color, sequence, and physical dimensions. A tool may open the artifact and still modify one property or ignore another. The evaluation records the result actually observed after re-import and does not presume that a category name guarantees compatibility.

Categories such as raster, vector, structured exchange, and preservation archive help plan a matrix without depending on a specific format. They describe general uses and expectations; they do not identify the internal encoding of the artifact. The criteria should be chosen by tool class and task, keeping external versions and settings documented when necessary for reproduction.


Open specifications and interchange tests help document which attributes can be represented and how an application should interpret them. The existence of a specification does not guarantee that every destination implements it in the same way. Evaluating re-import in another tool verifies effective compatibility for the chosen combination, without inferring universal support. The categorization of destinations in this article avoids depending on specific names and focuses on reading, editing, and reproduction tasks [22, 23].

### 2.3 Preservation and downstream uses

Digital preservation involves keeping content accessible, interpretable, and usable over time. The archival literature distinguishes preserving visual appearance, preserving editable structure, and maintaining contextual information. These goals may diverge. A reference copy may document the drawing, while a vector artifact may favor editing. The evaluation in this article focuses on geometry, but recognizes that durability and metadata are additional dimensions.

Studies of image quality and graphic reproduction show that requirements for color, scale, and contour vary depending on viewing, printing, and documentation. The downstream task defines which divergence is acceptable. A tolerance that is useful for editing a draft may not be sufficient for reproducing a piece at a defined size. Validation must include the destination medium and record how the reference was scanned.

The gap is a protocol that connects geometric aspects to downstream uses and tests the export through external comparison and re-import. The literature offers methods for evaluating shapes, exchange standards, and preservation, but not a universal criterion for drawings captured on paper. This article organizes these dimensions without claiming broad compatibility or fidelity already demonstrated.


Reports on the significant properties of vector images help make explicit which characteristics deserve to be preserved. Metadata vocabularies and institutional preservation recommendations also distinguish content, representation, and future access [21, 24, 25]. These materials are not all experimental articles; they serve as technical sources for the framework of uses. Long-term preservation is broader than geometric fidelity, but it influences which measures must remain interpretable when the file is consulted in another tool or period.

**Limits on the transfer of metrics.**

Metrics developed for natural images or technical drawings may not represent the experience of editing a sketch. A mean error may ignore a crossing that changes the reading, while a perceptual measure may tolerate a displacement that affects alignment. The literature provides instruments that must be validated for the content and the task. The gap here is not to invent a universal metric, but to connect independent dimensions with uses and references, declaring where a comparison is not sufficient.

## 3. Problem framing

Fidelity is defined by the relation between a reference drawing and the artifact one wishes to use later. The concept separates six aspects. **Position** describes the relative location of marks and elements on the page. **Scale** concerns the proportion between elements and the dimensions of the drawing in the destination medium. **Width** describes the apparent width of the strokes. **Shape** covers contours, curves, junctions, and terminations. **Order** records the relative sequence in which the strokes were produced, when this information is available in the reference. **Color** describes the hue and contrast of the marks relative to the paper.

Each aspect supports different uses. Editing may require selectable shapes and preserved order; documentation may prioritize position, appearance, and color; printing may depend on scale, width, and physical proportions; integration may require that elements remain distinguishable in another tool. A task may combine uses, but the criteria must be recorded separately. The table relates aspect, application, and external measure, without assuming that a single score determines usefulness.

**Table 1.** Relationship between aspects of geometric fidelity, downstream uses, and external measures, without presuming that a single measure serves all editing, documentation, printing, and integration contexts.

| Aspect | Relevant uses | Proposed external measure |
|---|---|---|
| Position | Editing, documentation, alignment | Displacement relative to reference points on the page |
| Scale | Printing, composition, integration | Ratio between corresponding dimensions and global proportions |
| Width | Legibility, printing, editing | Width difference along comparable segments |
| Shape | Editing, documentation | Distance between contours and preservation of junctions |
| Stroke order | Editing, activity review | Comparison of the recorded sequence with independent annotation |
| Color | Documentation, reproduction | Color difference under a declared viewing condition |

Position should be measured relative to a stable reference, such as the edge of the page or drawing points selected before the comparison. This measure does not confuse a global displacement of the sheet with a change in one part of the stroke. Scale is examined relatively and, when the use requires physical dimensions, relative to the intended size. A rescaled image may look the same on screen and diverge in print; the medium of use is part of the evaluation.

Width and shape are related, but not identical. A stroke may keep its central path and change width; another may keep its mean width and alter its curves or terminations. The measures must allow both to be observed. Contour analysis may be sensitive to the reference scan, whereas width may vary along the same gesture. The manual defines how to choose comparable segments and presents annotation uncertainty.

Stroke order is evaluated only if there is a reference source capable of establishing it. A static image of the final drawing can confirm shape and position, but not the temporal sequence. In that case, order is reported as not assessable, rather than inferred from appearance. Color also depends on lighting, scanning, and screen; the team records the reference condition and avoids interpreting viewing differences as export alteration without control.

The artifact may be considered geometrically faithful for one use and inadequate for another. A color change may be tolerable in an editing draft and unacceptable in colorimetric documentation. A small scale deviation may be irrelevant in a thumbnail and important in printing. For this reason, the team defines representative tasks and justifies criteria with use requirements, applicable standards, or user evaluation. The proposal does not choose universal values.

The interpretation of each aspect must consider the unit of comparison. Position may be global or local; shape may consider a single stroke or the whole set; color may describe a mean value or the variation along the mark. The team defines this unit in advance. If a drawing contains several types of stroke, summarizing by the mean may hide an altered subset. Distributions per drawing and per aspect give more context than an overall rating.

The use tolerance is not inferred from the variability of the reference alone. A measure may be precise and still not reflect the requirement of a person who edits or prints. Formal requirements, the destination task, and user evaluation can guide the choice. If no requirement is available, the article recommends reporting the divergence and avoiding a binary fidelity label.

Figure 1 shows the external path between page, system, and use of the file. Figure 2 compares reference and export by means of schematic strokes, without claiming that the shape represents a result. Figure 3 reserves a compatibility matrix for destination categories. These images organize the evaluation questions; they do not show an internal format, real support, or measurement.

![](figures/09-papel-arquivo.svg)

**Figure 1.** Conceptual view from paper to the exported artifact and to downstream use. The system appears as a black box, without showing an internal format or representation; author's own work.

## 4. Proposed evaluation protocol

The study uses a set of reference drawings that covers sparse and dense marks, straight and curved lines, crossings, and color variations pertinent to the question. Each drawing is made on paper and scanned independently to serve as a visual reference. If stroke order is evaluated, the sequence is annotated during execution or obtained through an independent record. The reference must be reviewed to identify changes caused by the scanning itself.

The exported artifact is evaluated in two situations: direct comparison with the reference and re-import into destination tools selected by use category. The categories include vector editing, raster viewing, printing, interchange with other tools, and archiving. The article does not name an internal format. The study records which destination class was used, how the artifact was opened, and which attributes remained available after re-import.

Conditions are paired by drawing and by task. The same reference may generate distinct comparisons for documentation, editing, and printing. The evaluation order is alternated to reduce familiarity effects. When possible, evaluators who measure the divergence do not know which artifact belongs to which condition. Cases in which a tool does not open the artifact are recorded as an interoperability failure of that combination, not excluded from the sample.

**Table 2.** Destination categories and verification criteria, relating editing, documentation, printing, and integration to measures of opening, editing, and preservation without naming specific internal formats.

| Destination category | Downstream use | External verification |
|---|---|---|
| Raster | Viewing and documentation | Compare rendered position, shape, width, and color |
| Vector | Element editing | Inspect selection and alteration of representable elements |
| Printing | Physical reproduction | Check output scale, width, proportion, and color |
| Interchange | Continuity between tools | Open and re-export in an independent tool |
| Archive | Future consultation | Check preservation of appearance and associated information |

Metrics are defined for each aspect. Position uses displacement relative to reference points. Scale compares proportions and dimensions relevant to the use. Width summarizes differences in width along annotated segments. Shape combines contour distances with verification of junctions and terminations. Order compares annotated sequences, when available. Color uses a declared measure under a controlled viewing condition. Results are presented separately before any synthesis.

Tolerance is justified by the use before collection. The team may derive it from a printing requirement, an editing need, user evaluation, or a documentation criterion. The chosen value is reported as a study decision, not as a universal property. When no external requirement exists, the study describes a divergence curve and leaves the interpretation to the reader, avoiding declaring “faithful” on the basis of an arbitrary threshold.

The analysis plan compares drawing by drawing and tool by category. For continuous measures, it presents the distribution, estimate, and uncertainty; for categorical attributes, it shows agreement and divergent cases. The sampling unit considers that several strokes of the same drawing share context. Correlated elements are not counted as independent drawings. If re-import alters several properties, each divergence is reported and the team does not attribute causality to one attribute without additional comparison.

The procedure includes review of the reference, inspection of outputs, and recording of failures. A sample is evaluated by more than one annotator to examine agreement in the choice of points, contours, and sequence. The team pre-registers exclusions, handling of incomplete drawings, and rules for the absence of known order. Figure 2 illustrates the comparison without values; Figure 3 organizes categories that still need to be tested.

The sample of drawings must record the diversity of stroke, density, shape, color, and overlap needed for the question. Inclusion criteria are applied before the comparison. An independently scanned reference is preserved without adjustment based on the output being evaluated. If it is necessary to align the images for a measure, the procedure is described as external preparation and its influence is examined in a sensitivity analysis. The team does not choose correspondence points after knowing the divergence.

Tool categories are selected according to intended real uses, not for isolated convenience. For each destination, the protocol records whether the artifact was opened, viewed, edited, or printed. Re-import is evaluated with known reference drawings and stored output copies. A tool that does not accept the artifact is recorded as an interoperability case, whereas one that opens it but alters attributes proceeds to the geometric measures.

Evaluators receive instructions to mark aspects independently. When the condition allows, the identification of the artifact is concealed during measurement. Agreement between annotators, task calibration, and reference uncertainty are reported. For color, the viewing condition and the observation device are described; for printing, medium, intended scale, and orientation are recorded. This information is necessary to interpret the measure, but does not reveal how the representation was constructed.

The analysis estimates the difference per drawing, aspect, and destination, using clustering that recognizes repetition of the same material. Use-defined tolerances are applied only after describing the continuous distribution of the divergence. The study reports measures below, within, and above the criteria only when these were grounded before collection. Compatibility is presented by category and task, with failure cases and uncertainty visible.

![](figures/09-sobreposicao-original-exportado.svg)

**Figure 2.** Schematic overlay of a reference drawing and an exported artifact, without representing a measure or result. The future comparison will use independent references and will provide methodological context; author's own work.

![](figures/09-matriz-compatibilidade.svg)

**Figure 3.** Empty compatibility matrix by destination category and use. The cells reserve space for a future evaluation and do not indicate support or a result; author's own work.

## 5. Structure of the results

This section reserves the reporting structure for a future evaluation. No measurements are provided in this article; therefore, no errors of position, scale, width, shape, order, or color are reported. The `[PENDING-DATA]` fields can only be filled after comparison with an independent reference, re-import, and review of the annotations. The following lines describe the organization of the results; they do not indicate values or current compatibility.

The report will present one row per drawing, aspect, and use category, with the tolerance defined before collection. Adequacy will be summarized separately for editing, documentation, printing, and integration. A combination without a test will be marked as not evaluated, not as incompatible or successful. Opening failures, changes in appearance, loss of editable structure, and absence of a reference for order will be reported in distinct categories.

**Table 3.** Structure for presenting divergences by drawing, aspect, and downstream use, keeping values and judgments as pending fields until the comparisons are reviewed, without anticipating measured performance.

| Drawing and use | Aspect | Divergence | Uncertainty and notes |
|---|---|---|---|
| Editing | Shape and order | [PENDING-DATA] | [PENDING-DATA] |
| Documentation | Position and color | [PENDING-DATA] | [PENDING-DATA] |
| Printing | Scale and width | [PENDING-DATA] | [PENDING-DATA] |
| Integration | Opening and preservation | [PENDING-DATA] | [PENDING-DATA] |

A future figure will show measured distributions or examples only when the references are available and the caption identifies the comparison method. Figure 2 of this article is schematic, and the matrix in Figure 3 remains empty. The results must include divergent cases, cases without a measure, and reference uncertainty. Visual examples are not selected after observing which ones seem to confirm the proposal.

## 6. Discussion

If position and shape are preserved but scale varies, adequacy will depend on the use. A documentation artifact on screen may remain useful, while a print at a specified dimension may fail to meet the requirement. The conclusion will not be “faithful” in general; it will indicate which aspects and tasks support the claim. This dimension-by-dimension reading makes explicit what an aggregate measure would hide.

A difference in width may affect legibility, appearance, and printing in distinct ways. The study describes where the width changed and how much the reference allows to be estimated, rather than treating every deviation as an equivalent error. If the change accompanies certain destination tools, the analysis reports the combination and does not attribute the cause to an internal stage. A contour measure may also capture width and shape at the same time, so separate metrics help interpret the pattern.

If shape is visually preserved but stroke order cannot be confirmed, the conclusion is limited to the final appearance. Order requires independent temporal data. Sequence is not inferred from crossings or overlaps without a previously validated rule. This distinction is especially important when the downstream use involves editing or review of the process, but may be irrelevant for a documentation image.

Color differences may stem from the scanned reference, the screen, the destination tool, or the export. A result must be interpreted under a controlled viewing condition and with a record of the material. If this condition is not available, color may be evaluated qualitatively or marked as inconclusive. This does not invalidate the geometry measures, but delimits which dimensions were verified.

A compatibility matrix may reveal that certain destination categories open the artifact while others lose properties. This conclusion is limited to the tools and tasks tested. The category does not represent all available programs nor future versions. The evaluation must record the combination, the opening procedure, the changes made, and whether the appearance or structure could be preserved when returning to the workflow.

The literature on vectorization and image comparison offers geometric measures, while studies of formats and preservation highlight access, interpretation, and structure [REFERENCES]. The protocol brings these perspectives together without reducing file quality to visual similarity. A raster representation may be adequate for documentation and insufficient for stroke editing. An editable structure may be adequate for alteration and require additional verification of printed appearance. The application decides which dimension weighs most.

A statistically detectable difference does not necessarily imply a perceptible or functional impact. The report distinguishes magnitude, uncertainty, and use tolerance. When there are participants, editing, printing, or organization tasks may help justify requirements, but they do not replace technical measures. Conversely, a small deviation may also be critical for scale or alignment. The conclusion remains tied to the defined context.

The study may find that an aspect was not preserved in a destination tool, or that the chosen criterion does not capture the desired use. In both cases, the observation guides revision of the task and the tolerance. The team does not correct the measure after seeing the result in order to make it look satisfactory. Methodological changes are recorded and a new collection is treated as a separate evaluation.

Finally, the results must separate technical compatibility, geometric fidelity, and usability. A file may open but alter the shape; preserve the shape but make editing difficult; or keep appearance and lose order. These situations are not contradictory. Reporting them by aspect and destination allows a more informed decision about use than a general success label.

The interpretation depends on which divergence occurs and in which use. A difference in position may affect alignment, while scale may be irrelevant in free viewing and critical for physical printing. Variation in width may be perceptible without displacing the contour, and a color difference may reflect the reference capture. Analysis separated by aspect avoids mixing causes and allows users to decide what is acceptable for their task.

If several dimensions are preserved in one destination category and not in another, the recommendation must be specific to the observed combination. It is not claimed that a category is universally compatible. A tool may change over time and its behavior depends on the task and on user options. Repeating the evaluation with different versions and conditions is necessary to broaden the conclusion.

The choice of tolerances may be contested. A printing requirement may provide a technical criterion, but other applications depend on user judgment. The article does not state that a tolerance chosen in one study serves everyone. The reader should be able to identify the source, context, and consequence of the criterion. If the study has no basis for a tolerance, presenting distributions and examples is more transparent than calling the result faithful or unfaithful.

## 7. Limitations and threats to validity

Construct validity depends on the chosen reference and on the metrics that represent each aspect. A scan may introduce distortion, and correspondence points may favor certain parts of the drawing. Contour measures may combine shape and width. The team describes how the reference was constructed and estimates annotator agreement. If the reference contains neither order nor physical dimensions, these aspects cannot be evaluated with the same rigor.

Internal validity is threatened by simultaneous changes in viewing, re-import, and destination tool. A difference observed after printing may combine file alteration, printer configuration, and physical material. The design must record these conditions and avoid attributing a single cause when they vary together. Paired comparisons and alternation of order reduce some effects, but do not eliminate residual confounding.

External validity is limited by the tool categories, paper types, drawing instruments, scans, and tasks included. A small matrix does not represent the entire software ecosystem. The evaluation describes selection criteria and avoids claiming universal compatibility. Version changes and user practices may alter the experience and need to be reassessed in later studies.

Data validity depends on consistent scans, a preserved reference, and enough metadata to identify the drawing and the use. Color depends on lighting and calibration; physical measures depend on reliable scale; order depends on temporal recording. Failures in these elements produce uncertainty that must be reported, not filled in by assumptions. Personal data or sensitive drawings require consent, minimization, and access control.

There is also a risk of selecting drawings that favor the chosen measures. A set composed only of simple strokes does not test junctions, overlaps, or changes in width. The sample design must include pertinent variety and report which cases are absent. A pilot helps discover whether the measures can be annotated, but does not guarantee that the selection covers all uses.

Finally, a black-box evaluation observes the artifact and its interaction with tools, but does not explain how the geometry is represented or produced. The causes of a divergence may remain unknown. This limitation prevents recommendations about internal parameters or transformations. The study supports claims about the outputs and conditions evaluated, not about the implementation.

## 8. Conclusion

This article proposes evaluating export fidelity along six aspects: position, scale, width, shape, stroke order, and color. Each dimension is related to editing, documentation, printing, and integration, with external measures and tolerances justified by use. The framework avoids treating fidelity as a single number or as universal compatibility.

The protocol combines a reference drawing, independent comparison, and re-import in categories of tools. It keeps the system as a black box and requires criteria defined before analysis. The figures and tables organize the evaluation, but do not present results or claims of support.

Varied drawings, reliable references, and tests on representative destinations are still needed. Future results should separate opening, geometric preservation, and suitability for the task. Until these observations exist, the fidelity achieved remains `[PENDING-DATA]`.

The proposal also helps distinguish interoperability from preservation. Opening a file in another tool confirms one form of access, not that all aspects have remained. A representation may preserve appearance and lose editable structure; another may preserve attributes but render differently. The interpretation relates each outcome to the need of use, in line with the literature on significant properties and preservation [21–25]. This relation, however, still needs to be tested with users and real artifacts.

Future research may extend the evaluation to legibility, metadata, accessibility, and long-term durability. These aspects complement geometric fidelity, but are not part of the conclusions of this protocol.

## Statements

- AI use: text drafted with the support of generative AI, with review and responsibility of the authors; references checked by DOI.
- Data: this proposal presents no experimental data; future references and artifacts will be described after collection.
- Code: there is no results-analysis code in this version; future materials will be identified by version.
- Conflict of interest: the authors shall declare any pertinent conflict before submission.
- Ethics: studies with participants or identifiable drawings will be submitted to the applicable ethical review before recruitment.
- Author contributions: the final version shall make the individual contributions of the authors explicit.

## References

[1] Liu, W.; Dori, D. From Raster to Vectors: Extracting Visual Information from Line Drawings. Pattern Analysis & Applications, 1999. https://doi.org/10.1007/S100440050010
[2] Hilaire, X.; Tombre, K. Robust and Accurate Vectorization of Line Drawings. IEEE Transactions on Pattern Analysis and Machine Intelligence, 2006. https://doi.org/10.1109/TPAMI.2006.127
[3] Chen, J. et al. Vectorization of Line Drawing Image Based on Junction Analysis. Science China Information Sciences, 2015. https://doi.org/10.1007/s11432-014-5246-x
[4] Chen, J. et al. An Improved Topology Extraction Approach for Vectorization of Sketchy Line Drawings. The Visual Computer, 2018. https://doi.org/10.1007/s00371-018-1549-z
[5] Das, A. K.; Langrana, N. A. Geometry Reconstruction of Vectorized Drawings Consisting of Orthographic Views. ASME Computers in Engineering Conference, 1996. https://doi.org/10.1115/96-DETC/CIE-1655
[6] Song, J. et al. Raster to Vector Conversion of Construction Engineering Drawings. Automation in Construction, 2002. https://doi.org/10.1016/S0926-5805(01)00069-3
[7] Nagasamy, V.; Langrana, N. A. Engineering Drawing Processing and Vectorization System. Computer Vision, Graphics, and Image Processing, 1990. https://doi.org/10.1016/0734-189X(90)90111-8
[8] Tian, X.; Günther, T. A Survey of Smooth Vector Graphics: Recent Advances in Representation, Creation, Rasterization, and Image Vectorization. IEEE Transactions on Visualization and Computer Graphics, 2024. https://doi.org/10.1109/TVCG.2022.3220575
[9] Bao, B.; Fu, H. Line Drawing Vectorization via Coarse-to-Fine Curve Network Optimization. Computer Graphics Forum, 2023. https://doi.org/10.1111/cgf.14787
[10] Zhang, Z. et al. Vectorizing Line Drawings of Arbitrary Thickness via Boundary-Based Topology Reconstruction. Computer Graphics Forum, 2022. https://doi.org/10.1111/cgf.14485
[11] Mo, H. et al. General Virtual Sketching Framework for Vector Line Art. ACM Transactions on Graphics, 2021. https://doi.org/10.1145/3450626.3459833
[12] Parakkat, A. D. et al. Color by Numbers: Interactive Structuring and Vectorization of Sketch Imagery. Proceedings of the CHI Conference on Human Factors in Computing Systems, 2021. https://doi.org/10.1145/3411764.3445215
[13] Xie, J. et al. Interactive Vectorization. Proceedings of the CHI Conference on Human Factors in Computing Systems, 2017. https://doi.org/10.1145/3025453.3025872
[14] Xie, G. et al. Hierarchical Diffusion Curves for Accurate Automatic Image Vectorization. ACM Transactions on Graphics, 2014. https://doi.org/10.1145/2661229.2661275
[15] Yan, C. et al. Deep Sketch Vectorization via Implicit Surface Extraction. ACM Transactions on Graphics, 2024. https://doi.org/10.1145/3658197
[16] Magne, T.; Sorkine-Hornung, O. Single-Line Drawing Vectorization. Computer Graphics Forum, 2025. https://doi.org/10.1111/cgf.70228
[17] Wang, Z. et al. Image Quality Assessment: From Error Visibility to Structural Similarity. IEEE Transactions on Image Processing, 2004. https://doi.org/10.1109/TIP.2003.819861
[18] Huttenlocher, D. P.; Klanderman, G. A.; Rucklidge, W. J. Comparing Images Using the Hausdorff Distance. IEEE Transactions on Pattern Analysis and Machine Intelligence, 1993. https://doi.org/10.1109/34.232073
[19] Wang, Z.; Simoncelli, E. P.; Bovik, A. C. Multiscale Structural Similarity for Image Quality Assessment. Asilomar Conference on Signals, Systems & Computers, 2003. https://doi.org/10.1109/ACSSC.2003.1292216
[20] Xu, B. et al. True2Form: 3D Curve Networks from 2D Sketches via Selective Regularization. ACM Transactions on Graphics, 2014. https://doi.org/10.1145/2601097.2601128
[21] Coyne, M. et al. The Significant Properties of Vector Images. JISC, 2007. https://www.webarchive.org.uk/wayback/archive/20140616090304/http://www.jisc.ac.uk/media/documents/programmes/preservation/vector_images.pdf
[22] W3C SVG Working Group. Scalable Vector Graphics (SVG) 1.1 (Second Edition). W3C Recommendation, 2011. https://www.w3.org/TR/SVG11/REC-SVG11-20110816.html
[23] International Organization for Standardization. ISO 19005-1:2005—Document Management—Electronic Document File Format for Long-Term Preservation—Part 1: Use of PDF 1.4 (PDF/A-1). ISO, 2005. https://www.iso.org/standard/38920.html
[24] Library of Congress; PREMIS Editorial Committee. PREMIS Data Dictionary for Preservation Metadata, Version 3.0. Library of Congress, 2015. https://www.loc.gov/standards/premis/v3/index.html
[25] Library of Congress. Preferences in Summary for Still Image Content. Library of Congress, 2024. https://www.loc.gov/preservation/digital/formats/content/still_preferences.shtml
