# Robustness of visual interpretation in everyday conditions

## Abstract

Camera-assisted drawing systems operate under changes in lighting, paper, and surroundings that are absent from controlled scenes. Evaluating only an ideal condition cannot show which changes accompany a loss of quality or whether different perturbations create similar difficulties. This article proposes a protocol for assessing robustness in everyday conditions without describing internal mechanisms. The framework organizes eight factors: glare, shadow, blur, noise, paper folds or wrinkles, background, paper color, and light source. For each factor, it defines an external observation, qualitative levels, and a way to vary the condition. Evaluation first compares each factor in isolation against a reference and then studies justified combinations. Measures include performance by condition, degradation relative to the reference, sensitivity across levels, and recovery after the scene returns to its initial condition. Tables and diagrams describe the catalog and study design. Since no measurements are available, the article assigns no effects to any factor, sets no acceptable limits, and reserves the results section for future data. The proposal provides a comparable vocabulary for documenting scenarios, uncertainty, and the scope of conclusions.

**Keywords:** robustness; real-world conditions; drawing; computer vision; evaluation

## 1. Introduction

An evaluation performed under uniform lighting, flat paper, and a simple background describes only part of the conditions in which drawings are produced. In everyday environments, light may reflect off the paper or be partially blocked; the sheet may have texture, color, or deformation; and nearby objects may be confused with the region of interest. In addition, the camera may record motion or loss of sharpness. These variations occur before and during capture and may coexist, although their effects are not necessarily equivalent.

The term robustness usually summarizes the maintenance of performance when inputs or conditions change. To be useful in an evaluation, this idea must be linked to an observable external condition, a task, and a defined response. "Real environment" is not a single condition: a table next to a window differs from a surface under diffuse light, even if both are described as indoor. The category also does not inform whether the page is flat, whether there is localized glare, or whether the framing includes competing objects. An explicit catalog helps turn this broad label into documentable variations.

This article proposes studying a camera-assisted drawing system as a black box. The analysis considers only the condition presented and the visible result for a previously defined task. The study does not attribute a variation to an internal stage, nor infer which factor was recognized. The question is: **how do everyday visual factors, evaluated in isolation and in planned combinations, relate to the observable quality of the interpretation of pages and drawings?** The formulation is associative because the protocol can be executed both in controlled sessions and in natural observation, and not every scenario allows causal manipulation.

The article offers three contributions. First, it presents an operational catalog of glare, shadow, blur, noise, paper deformation, background, paper color, and light source. Second, it proposes an evaluation sequence that separates isolated variations from combinations, with a common reference and recording of the condition. Third, it defines measures to compare performance, degradation, sensitivity, and recovery, accompanied by limits for interpretation. These contributions specify a protocol, not an experimental result nor a claim that the system maintains or loses quality under any factor.

Section 2 situates the work in the literature on visual corruptions, documents captured in uncontrolled environments, and robustness evaluation. Section 3 defines the perturbations and how to record them without assuming a response. Section 4 describes conditions, collection, measures, and analysis. Section 5 reserves the results tables for a later evaluation. Section 6 discusses how to interpret possible patterns, and Section 7 delimits threats to validity. Section 8 synthesizes the proposal and the evidence required.

The catalog does not aim to cover every phenomenon in a scene. Perspective, sheet movement, occlusion, dirt, transparency, wear, compression, and differences between devices may also alter observation. Some of these aspects have their own protocols in the other articles of the collection. Here, the selection prioritizes environmental and material factors that can be described independently and manipulated in controlled studies. The choice reduces the breadth of the problem to make the comparisons more interpretable.

It is also important to distinguish an adverse condition from a failure. A scene with shadow is not automatically invalid; it may be a normal occurrence of the task. Performance must be observed for a defined purpose, such as locating the page or preserving the marks of the drawing. Without this purpose, "robust" becomes an adjective without criteria. The protocol therefore requires a task and an external reference before comparing conditions.

The study does not presume that all people encounter the same environments, nor that a simulated condition reproduces everyday diversity. Controlled evaluation allows isolating changes, while collection in natural use improves representativeness and introduces confounders. The two approaches answer different questions. Recording the origin of each scene, its known conditions, and the mode of exposure allows readers to assess this difference without interpreting a laboratory scenario as a universal portrait.

## 2. Related work

### 2.1 Visual corruptions and variations

Robustness studies in computer vision organize input changes into families such as noise, blur, contrast, compression, and weather or lighting changes. Common corruption benchmarks are useful because they keep a reference task and apply controlled transformations, allowing sensitivity to be examined without confusing each change with another [1, 3, 8]. They also highlight that performance on a familiar distribution does not guarantee equivalent behavior on modified images. Natural adversarial examples, background diversity, and out-of-distribution evaluations show other aspects of this difference [2, 4, 6, 7, 9]. However, a transformation applied to generic photographs does not automatically represent paper, ink, specular glare, or the shadows of a drawing activity. The type of content, the scale, and the success criterion must be considered before transferring conclusions.

Research on image quality and photographic capture distinguishes sharpness, noise, exposure, tonal range, and color reproduction. The same scene may change with the source, position, and spectrum of illumination, as well as with the reflective properties of the surface. Glare and shadow are particularly relevant because they alter local visibility, while blur affects the limits of marks and edges. These dimensions motivate a catalog in which the condition is recorded separately from the response, instead of being summarized by a generic notion of "bad image".

A methodological difficulty is that the names of perturbations do not always correspond to independent interventions. Changes in the light source may alter brightness, shadow, color balance, and exposure simultaneously. A crumpled sheet may generate new shadows and modify the apparent plane. Isolated evaluation requires checking which properties actually changed and recording side effects. Controlled benchmarks provide precedents for decomposing variations, but the physical scene requires additional documentation and visual verification.

### 2.2 Documents in uncontrolled environments

Camera capture of documents is studied in scenarios with tilted, deformed, shaded, or partially illuminated pages. Datasets and evaluation methods explore edge detection, rectification, shadow removal, and page unwarping [10–13]. These tasks relate to drawing because they share paper, marks, and capture under variable illumination. Still, the quality of a legible image is not equivalent to the preservation of all strokes: an operation that improves text contrast may erase or alter faint marks. The metric must correspond to the use, and the evaluation must not assume that results on printed documents extend to hand-drawn sketches.

Collections of natural scenes and mobile-capture benchmarks help study framing, background, and illumination outside studios. The variation between environments may reflect differences in camera, distance, orientation, and processing, in addition to the desired visual condition. When all of these change together, a comparison cannot identify which factor accompanies the difference. Document binarization contests and quality evaluations offer precedents for criteria and common collections [14–17, 24]. For this reason, the proposal records the available capture information and separates single-factor tests from a combined phase.

A set of photographed documents also depends on the diversity of the documents themselves. Printed sources, handwritten annotations, ink contrasts, and page backgrounds may produce very different distributions. Aggregate metrics over a single collection do not necessarily describe behavior on another set. Shared evaluations offer common rules and references, but interpretation must consider annotation criteria, the origin of the images, and the type of degradation included. This concern guides the documentation of the sample in this article: the condition must be characterized together with the evaluated content, without assuming that the word "document" represents a homogeneous visual class.

Work on folded documents and images with shadows shows that page geometry and illumination can interact [10–12]. A shadow may be cast by the environment or created by the curvature of the paper itself. An evaluation that classifies both as "shadow" may mix distinct origins; the protocol notes whether the paper appears flat and whether the dark region follows an observable fold. The distinction is descriptive and does not aim to recover the physical cause with certainty.

### 2.3 Robustness evaluation

Evaluation strategies vary among controlled stress testing, testing in natural environments, and distribution shift. Controlled testing makes it easier to attribute differences to isolated factors, while natural collection shows the mixture of conditions found in use. Robustness evaluations also warn against relying on a single indicator: an average may hide failures concentrated in one condition or one task. Distributions by scenario, measures of uncertainty, and disaggregation by participant or session make the report more informative.

Sensitivity approaches analyze how much a measure varies as the condition changes. The shape of the relation may be gradual, discontinuous, or dependent on a combination. The protocol does not assume a monotonic curve: a more intense perturbation may affect one task little and another a lot; the response may also saturate or oscillate. Reporting the sequence of levels and the reference condition is necessary to interpret any curve. Specific studies of document degradation, shadow, glare, exposure, and blur exemplify the diversity of phenomena that can be evaluated separately [17–23, 25]. The illustrative figures of this proposal do not replace data nor anticipate a trend.

The gap addressed is methodological. There is work on image corruptions, document capture, and evaluation in diverse environments, but their factors and outcomes do not always align with the interpretation of drawing on paper. For this scenario, a concise catalog is lacking that unites external measures of condition, isolated and combined exposure, and observable responses without specifying the interior of the system. This article proposes such a structure as a basis for studies that must declare task, sample, and conditions. The taxonomy should be revised if future literature or collection reveals relevant missing factors.

### 2.2 Documents in uncontrolled environments

[Literature on page capture, everyday scenes, and benchmarks.]

### 2.3 Robustness evaluation

[Literature on isolated and combined evaluation; make the gap explicit.]

## 3. Problem framing

Robustness is treated as the variation of the observable response between a reference condition and conditions that alter the scene. The comparison requires that the task, the material, and the definition of the outcome remain clear. Each perturbation is described by three fields: the visual property to record, the way to establish qualitative levels, and the mode of variation. The word "level" indicates an ordering defined by the protocol, not an internal value or a result. If two properties change at the same time, the scene belongs to the combination stage and must not be labeled as an isolated test.

The catalog includes eight factors. **Glare** is a region of brightness that reduces local contrast; it can be annotated by location and relative area, using documented surface and illumination. **Shadow** is a darkened region that crosses or borders the page; its position, extent, and relation to the drawing are recorded. **Blur** is the apparent loss of sharpness at the edges; it may be graded by the quality of an external visual reference, without deducing its origin. **Noise** is visual variation not belonging to the drawing, described by its distribution and apparent intensity in areas without ink. These factors may arise together, but must be separated in the controlled study.

**Fold and wrinkle** describe visible deformations of the support, including creases and undulations. The record indicates presence, location, extent, and whether the page remains resting or raised. **Background** describes what appears around the sheet, including contrast, texture, and competing elements; the annotation distinguishes a uniform background from a visually complex surface without naming identifiable objects. **Paper color** records variations of tone and finish, including colored or aged pages when they are part of the scope. **Light source** describes origin, relative position, diffusion, and consistency during the session, since these characteristics may change glare and shadow.

**Table 1.** Catalog of perturbations with an observable form of measurement and planned variation, allowing the conditions to be described without presupposing internal mechanisms or system-specific causal relations, for future comparison across studies.

| Perturbation | External record | Planned variation |
|---|---|---|
| Glare | Location and extent of the brightness | Qualitative conditions of brightness absent, localized, or broad |
| Shadow | Area, position, and relation to the drawing | Shadow absent, lateral, or crossing the page |
| Blur | Visual sharpness of reference edges | Conditions of sharp focus and gradual loss of sharpness |
| Noise | Variation in regions without ink | Clean scene and increasing visual levels of noise |
| Fold or wrinkle | Location and extent of the deformation | Flat support and documented deformations |
| Background | Contrast and texture around the sheet | Simple background and backgrounds with distinct visual complexity |
| Paper color | Recorded tone and finish | Papers with different appearances, keeping the task |
| Light source | Position and diffuse or direct character | Documented lighting configurations |

Qualitative levels must be defined with visual examples and reviewed in the pilot. There is no universal cut-off separating a "light" shadow from a "strong" one, since appearance depends on paper, exposure, and region of interest. An ordinal description makes it possible to organize conditions without claiming a non-existent physical scale. Whenever there is a measuring instrument, its limits and uncertainty are reported; when classification is visual, the manual and the agreement between annotators are presented.

The observable response must reflect the chosen task. In a localization task, one may report whether the page was found according to an annotated reference. In a preservation task, the observed drawing may be compared with an independent scan. The study may also evaluate availability, continuity, legibility, or recovery, provided that each outcome has its own definition and reference. These responses should not be combined into a single score without justifying the relation between them.

Environmental factors are not necessarily independent or gradual. Glare may cover a different region depending on orientation; a fold may alter the apparent background by creating a shadow; noise may become more visible on low-contrast paper. The taxonomy records each factor separately and reserves combinations for a later stage. A natural scene may contain multiple factors and be classified in more than one category, but should not be treated as isolated evidence for any of them.

The framework also distinguishes a planned perturbation from a covariate. A camera change may accompany a lighting test without being part of the intended factor. If it cannot be kept constant, it must be recorded and included in the interpretation. Reference conditions are repeated throughout collection to check for temporal drift and context change. The reference is a condition defined for that study; it is not equivalent to a universal standard of perfect scene.

Figure 1 gathers schematics of the catalog's factors. The figure presents visual categories, not their prevalence nor the expected response. The separation into panels helps plan variations, but does not imply that each factor can be produced or measured without collateral influence. The details for establishing the conditions are described in the protocol and in the collection annotations.

![](figures/06-catalogo-perturbacoes.svg)

**Figure 1.** Conceptual catalog of glare, shadow, blur, noise, paper deformation, background, color, and lighting. The icons are schematic, without portraits of scenes or results; author's own work.

## 4. Proposed evaluation protocol

The study begins with a documented reference and a constant task. In the first stage, one factor is varied at a time, keeping the others as stable as possible. The order of conditions is alternated or randomized when this does not compromise control, reducing association between condition and fatigue, warm-up, or scene drift. Each condition is captured in more than one session or planned repetition according to the design, and the repetition rule is published before analysis. The article does not fix a sample size, because it depends on variability and on the minimum relevant effect, which still need to be defined from a pilot and the scientific objective.

In the second stage, combinations selected with justification are tested. A complete factorial design may become excessive as factors and levels multiply. A balanced sample may prioritize plausible interactions, such as glare with light source or fold with shadow, without claiming that these combinations are the only important ones. The team documents which combinations were chosen and which were left out. If collection is natural, the coexisting categories are annotated and the analysis describes associations, avoiding improper causal attribution.

Capture must include an independent reference that allows classifying condition and response. This may involve scene annotations, an image or scan of the drawing reference, and external recording of the sequence. The chosen method depends on the outcome and must be described without exposing internal details. The team confirms that the reference material was not altered by the condition in a way that prevents comparison. Images with annotation doubts are flagged and submitted to adjudication by a predefined rule.

Measures are defined before collection. **Performance by condition** summarizes the main outcome in each combination. **Relative degradation** compares the measure in a perturbed condition with the reference, using a definition that keeps direction and scale interpretable. **Sensitivity** describes how the response changes across ordered levels of the same perturbation. **Recovery** records whether the response returns when the scene goes back to the reference, including time or state only if the task allows a clear external definition. In addition, missing data, persistent failures, and annotation uncertainty are reported.

**Table 2.** Metrics to summarize reference performance, degradation, sensitivity, and recovery, with external definitions and interpretive limitations declared before collection, without imposing causal interpretations or confusing distinct measures.

| Metric | Operational definition | Summary | Limitation |
|---|---|---|---|
| Performance by condition | Outcome defined in advance for each scene | Distribution and uncertainty by condition | Depends on the task and the reference |
| Relative degradation | Difference or ratio relative to the reference condition | Paired estimate per session | The direction depends on the original metric |
| Sensitivity | Observed change between levels of the same factor | Slope or ordered contrast | Qualitative levels may not be equally spaced |
| Recovery | Return to the reference outcome after the condition is removed | State or time to return | Requires defining the end of the perturbation |
| Persistent failure | Absence of the outcome until the end of observation | Count and proportion per condition | Not to be confused with the end of a session |
| Annotation uncertainty | Divergence between classification and reference | Agreement and adjudicated cases | Does not replace the validity of the reference itself |

The analysis plan presents the distribution of each outcome before any synthesis. For continuous measures, central estimates and appropriate uncertainty intervals are reported; for categories, frequencies by condition are shown. The grouping unit must reflect the design, because repeated observations of the same person or sheet are not independent. Main comparisons are paired whenever the collection allows. The analysis does not retrospectively select the metric that produces the strongest difference.

The degradation assessment compares each condition with its corresponding reference, preserving pairing by person, task, and session when available. Sensitivity may be estimated by ordered contrasts between levels, but equal distance between categories such as "low", "intermediate", and "high" is not presumed. A curve figure uses qualitative form only to explain the future presentation. Data will be shown with points or distributions and not replaced by a smoothed line without explanation.

The protocol includes quality control. The team verifies whether each intended factor was actually altered and whether important covariates remained constant. A sample of the scenes is evaluated by independent annotators who do not know the outcome of the condition whenever possible. Differences are discussed by the manual and an adjudication rule, with the agreement reported. The sequence of reference and response files is documented sufficiently for auditing, without disclosing unnecessary identifiable information.

If the combined condition shows degradation different from that expected from the isolated factors, the report presents this interaction as an observation of the drawing and delimits its interpretation. It may be that one perturbation reduces the visibility of another, or that their effects reinforce each other; neither possibility should be presumed. An exploratory study may identify combinations for later investigation, but does not support a broad recommendation without repetition and variety of environments.

Figure 2 shows the blocks of the protocol: reference, isolated variation, and planned combinations. Figure 3 is an illustrative curve of the possible shape of degradation. Both communicate a test structure and contain no values. The evaluation should present its own graphs with identified conditions, individual observations where appropriate, and uncertainty intervals.

The design considers ethics and privacy when collection includes people, domestic spaces, or potentially identifiable drawings. Consent states the purpose, visual recording, retention, and sharing. Personal elements around the sheet are removed or protected before any publication. The data access policy is described even if full sharing is not possible. Access restrictions are part of the interpretation of reproducibility and must not be omitted.

![](figures/06-protocolo-variacao.svg)

**Figure 2.** Conceptual sequence of comparison between reference condition, isolated perturbation, and planned combinations. It describes evaluation blocks, not internal steps of the system; author's own work.

![](figures/06-curva-degradacao.svg)

**Figure 3.** Illustrative curve of degradation according to the qualitative intensity of a perturbation. There are no values on the axes and no measured data; the expected form is not a result; author's own work.

## 5. Structure of the results

This section reserves the presentation of a future evaluation. No measurements are provided for this article, so no differences, rates, percentages, or rankings among perturbations are reported. The fields marked `[PENDING-DATA]` can only be filled in after collection, review of the annotations, and the corresponding analysis. The table records the structure of the report and does not encode an expected result.

The first summary reports which conditions were actually captured, which remained absent, and how the condition was verified. For each factor, the reference, the observed levels, the number of experimental units, and the justified exclusions are described. A planned condition that did not occur must remain identified as not collected, rather than disappearing from the report. The selected combinations and the reason for including them are also reported.

**Table 3.** Presentation model for future results by factor, with separate fields for condition, observations, measure, and uncertainty; empty spaces do not represent estimates or empirical differences.

| Factor and level | Observations | Main measure | Uncertainty and notes |
|---|---|---|---|
| Glare | [PENDING-DATA] | [PENDING-DATA] | [PENDING-DATA] |
| Shadow | [PENDING-DATA] | [PENDING-DATA] | [PENDING-DATA] |
| Blur and noise | [PENDING-DATA] | [PENDING-DATA] | [PENDING-DATA] |
| Paper, background, and lighting | [PENDING-DATA] | [PENDING-DATA] | [PENDING-DATA] |

A complete presentation separates the distribution by condition from the comparison with the reference. The graph should identify the task and the outcome, show the observations or their distribution, and explain any aggregation. If a combination of factors is shown, the legend will indicate which conditions coexisted. An estimate without visible observations or a measure of uncertainty may hide the concentration of the data and should be avoided.

Figure 3 of this article is only a conceptual curve. No empirical point or interval is available. If future data do not support a monotonic curve, the visualization should reflect that shape or use categorical comparisons, without adjusting the observation to the visual expectation of the scheme. The report should also distinguish missing result, inconclusive measure, and persistent failure, preserving the reason for each case.

## 6. Discussion

The protocol allows examining whether environmental conditions are associated with changes in the task, without presuming that a perturbation is always harmful. If a measure varies with the presence of glare, for example, the result will still depend on the position of the brightness, the active stroke, the paper, and the illumination. An aggregate association may hide differences between regions. The discussion must present these conditions and avoid turning the factor's name into a sufficient explanation.

If an isolated factor accompanies a change and the others do not, the first question is whether the intervention managed to separate the intended conditions. A change of light source, for example, may simultaneously alter shadow and apparent color. An effect attributed to the isolated factor would be fragile if these variables were not recorded. The interpretation must report both the planned and the observed condition and discuss deviations from the design before proposing explanations.

If a combination produces a response distinct from the isolated conditions, there may be an interaction between factors or a difference in the distribution of the scenes. The interaction does not by itself demonstrate a physical mechanism nor generalization to another environment. It points to a condition to investigate with repetition and better control. The literature on corruption benchmarks and adverse conditions shows the usefulness of distinguishing controlled changes from natural images; its findings support the design, but do not predict the response of the drawing on paper [1–8].

A drop only in preservation tasks, with no change in general localization, would indicate that a broad summary of success is insufficient. This possibility reinforces the use of metrics tied to the objective. A measure of reading or page detection does not necessarily assess the integrity of fine strokes. Studies of degraded documents and quality evaluation help show how the task defines the meaning of "good result", but drawings have a visual distribution and use different from printed text [10–17, 24].

It is also possible that there is little or no difference across the conditions tested. This would not mean universal robustness. The result would only be informative for the variety of scenes, task, and population observed, with power to detect relevant differences. Low-intensity conditions, a concentrated sample, or imprecise measures may hide associations. The report must present uncertainty and the coverage of the study, instead of summarizing the finding as an absence of sensitivity.

The catalog emphasizes separate factors because this decomposition facilitates comparison. However, everyday scenes are compound: paper, light source, shadow, and background may vary together. Benchmarks with controlled corruptions enable systematic comparison, whereas natural sets capture part of the complexity and diversity of the real world [1, 4, 6, 7]. A useful approach combines the two perspectives. Isolated tests help understand specific associations; natural evaluations verify whether the chosen factors and interactions are relevant in context.

Work on shadow removal, specular glare, and document correction shows that these phenomena are treated as distinct tasks and that there are specialized datasets for each [17–23]. The article does not propose applying these transformations to the output nor adopting a correction technique. The relevance of the literature lies in showing differences between phenomena that a broad label of visual quality would hide. Future evaluation should separate description of the condition, observed response, and intervention for improvement.

The comparison between flat and deformed paper is another example of caution. A fold may alter apparent position, illumination, and focus, so its effect is not merely "more texture". External recording of the deformation and its relation to the active region allow discussing which situations were included. Results on document unwarping may inform the physical characterization, but do not establish that a drawing will be interpreted or preserved with the same quality [10–12].

A practical consequence of the structure is that recommendations should only emerge after replication in distinct scenarios. If the response varies between paper classes or light sources, generic recommendations may be inadequate. The protocol can guide a matrix of conditions of use, but choosing an acceptable condition belongs to the application and to user requirements. The team presents evidence and uncertainty; the product decision should not be disguised as a universal scientific threshold.

Finally, the proposal encourages reporting negative results and conditions not evaluated. Benchmarks tend to highlight publishable sets and metrics, but a robustness study must also state which combinations were not tested and which scenes were not represented. This transparency reduces conclusions that go beyond the data and makes it easier to choose the next experiment. Without collection, every interpretation in this section remains conditional.

## 7. Limitations and threats to validity

Construct validity depends on the correspondence between the factors and real phenomena. "Glare", "shadow", and "noise" may gather distinct causes or appearances. Ordinal levels do not ensure equal intervals, and the qualitative description may diverge among annotators. The protocol proposes recording external properties but does not eliminate the ambiguity of classification. The manual, the pilot review, and the agreement must be reported so that this uncertainty can be judged.

The performance metric may represent only part of the quality of the drawing. Success in locating a page does not guarantee preservation of strokes, just as legibility does not guarantee temporal continuity. Using too many measures increases the risk of selective analysis; using only one may hide important differences. The team must justify the main outcome, report secondary outcomes as such, and keep definitions separate when they express distinct properties.

Internal validity is threatened by covariation. Light source, exposure, paper orientation, and distance may change together with a perturbation. Planned manipulation may introduce artifacts that would not arise in natural use, while natural observation does not allow simple causal attribution. Order alternation, repetition of references, and documentation of the scenes reduce part of these risks, but do not prove that all observed differences derive from the named factor.

External validity is delimited by the paper, drawing, camera, environment, and participants included. A laboratory session may not represent a home, classroom, or public space. Types of ink, texture, color, and drawing practice also vary. The sample and context must be reported; generalization to all everyday conditions should not be made from a few configurations. Later evaluations in diverse places and materials are needed to broaden the scope.

Data validity depends on adequate reference and synchronization. A scan may differ from the original in scale, illumination, or deformation. Annotation may not distinguish a faint mark from noise, and a region of glare may hide information that the reference cannot reconstruct. Changes of condition during the session may also go unrecorded. The protocol makes these limits explicit and keeps uncertain observations flagged, but collection may remain incomplete.

There are sampling and analysis threats. Rare conditions may appear seldom; participants may contribute different numbers of scenes; and a sequence of correlated images may inflate the impression of sample volume. The unit of analysis and the grouping structure must correspond to the design. Aggregate results without this distinction may underestimate uncertainty. A prior analysis plan helps avoid choices guided by the observed pattern, without guaranteeing that the statistical model is adequate.

Finally, the black-box evaluation restricts internal causal explanations. The protocol can indicate that a condition accompanies a visible change, but does not identify which component or rule produced the result. This limitation is intentional in order to keep the comparison external, but it reduces diagnostic value. The article does not allow reconstructing the implementation and must not be used to claim robustness under conditions that were not effectively observed.

## 8. Conclusion

This article proposes a protocol for studying robustness in everyday scenes through eight observable perturbations: glare, shadow, blur, noise, paper deformation, background, color, and light source. The structure separates isolated variations from combinations and relates the conditions to performance, degradation, sensitivity, and recovery, without revealing internal mechanisms.

The proposal organizes collection and reporting, but does not establish which factors affect interpretation nor at what intensity. The figures are conceptual and the results section remains reserved for real data. The literature on visual corruption, document capture, and uncontrolled environments grounds the dimensions, without guaranteeing transferability to drawings.

The next step is to execute the protocol with a clearly defined task, verify the recorded conditions, and fill the `[PENDING-DATA]` fields with observations and uncertainty. Conclusions must remain limited to the materials, participants, and scenes evaluated. Only replications in diverse environments can support broader recommendations.

## Statements

- Use of AI: text drafted with the support of generative AI, with review and responsibility of the authors; references checked by DOI.
- Data: this article does not present experimental data; future observations will be identified and described after collection.
- Code: there is no results analysis code in this proposal; future materials will be identified by version.
- Conflict of interest: the authors must declare any relevant conflict before submission.
- Ethics: studies with participants or images of private spaces will be submitted to the applicable ethical review before recruitment.
- Author contributions: the final version must make the individual contributions of the authors explicit.

## References

[1] Hendrycks, D.; Dietterich, T. Benchmarking Neural Network Robustness to Common Corruptions and Perturbations. International Conference on Learning Representations, 2019. https://openreview.net/references/pdf?id=r1vn4B3W4
[2] Hendrycks, D. et al. Natural Adversarial Examples. IEEE/CVF Conference on Computer Vision and Pattern Recognition, 2021. https://doi.org/10.1109/CVPR46437.2021.01501
[3] Hendrycks, D. et al. The Many Faces of Robustness: A Critical Analysis of Out-of-Distribution Generalization. IEEE/CVF International Conference on Computer Vision, 2021. https://openaccess.thecvf.com/content/ICCV2021/html/Hendrycks_The_Many_Faces_of_Robustness_A_Critical_Analysis_of_Out-of-Distribution_ICCV_2021_paper.html
[4] Sakaridis, C. et al. ACDC: The Adverse Conditions Dataset With Correspondences for Semantic Driving Scene Understanding. IEEE/CVF International Conference on Computer Vision, 2021. https://doi.org/10.1109/ICCV48922.2021.01059
[5] Sakaridis, C.; Dai, D.; Van Gool, L. Semantic Foggy Scene Understanding with Synthetic Data. International Journal of Computer Vision, 2018. https://doi.org/10.1007/s11263-018-1072-8
[6] Barbu, A. et al. ObjectNet: A Large-Scale Bias-Controlled Dataset for Pushing the Limits of Object Recognition Models. Advances in Neural Information Processing Systems, 2019. https://proceedings.neurips.cc/paper/2019/hash/97af07a14cacba681feacf3012730892-Abstract.html
[7] Koh, P. W. et al. WILDS: A Benchmark of in-the-Wild Distribution Shifts. Proceedings of the International Conference on Machine Learning, 2021. https://proceedings.mlr.press/v139/koh21a.html
[8] Croce, F. et al. RobustBench: A Standardized Adversarial Robustness Benchmark. NeurIPS Datasets and Benchmarks, 2021. https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/a3c65c2974270fd093ee8a9bf8ae7d0b-Abstract-round2.html
[9] Wang, H. et al. Learning Robust Global Representations by Penalizing Local Predictive Power. Advances in Neural Information Processing Systems, 2019. https://www.cs.cmu.edu/~epxing/papers/2019/Wang_etal_nips19.pdf
[10] Ma, K. et al. DocUNet: Document Image Unwarping via a Stacked U-Net. IEEE/CVF Conference on Computer Vision and Pattern Recognition, 2018. https://openaccess.thecvf.com/content_cvpr_2018/papers/Ma_DocUNet_Document_Image_CVPR_2018_paper.pdf
[11] Das, S. et al. DewarpNet: Single-Image Document Unwarping With Stacked 3D and 2D Regression Networks. IEEE/CVF International Conference on Computer Vision, 2019. https://doi.org/10.1109/ICCV.2019.00022
[12] Verhoeven, F.; Magne, T.; Sorkine-Hornung, O. UVDoc: Neural Grid-based Document Unwarping. SIGGRAPH Asia Conference Papers, 2023. https://doi.org/10.1145/3610548.3618174
[13] Nayef, N. et al. SmartDoc-QA: A Dataset for Quality Assessment of Smartphone Captured Document Images—Single and Multiple Distortions. International Conference on Document Analysis and Recognition, 2015. https://doi.org/10.1109/ICDAR.2015.7333960
[14] Gatos, B.; Ntirogiannis, K.; Pratikakis, I. DIBCO 2009: Document Image Binarization Contest. International Journal on Document Analysis and Recognition, 2010. https://doi.org/10.1007/s10032-010-0115-7
[15] Pratikakis, I.; Gatos, B.; Ntirogiannis, K. ICDAR 2011 Document Image Binarization Contest (DIBCO 2011). International Conference on Document Analysis and Recognition, 2011. https://doi.org/10.1109/ICDAR.2011.299
[16] Pratikakis, I.; Gatos, B.; Ntirogiannis, K. ICDAR 2013 Document Image Binarization Contest (DIBCO 2013). International Conference on Document Analysis and Recognition, 2013. https://doi.org/10.1109/ICDAR.2013.219
[17] Zhou, Y. et al. A Review of Document Image Enhancement Based on Document Degradation Problem. Applied Sciences, 2023. https://doi.org/10.3390/app13137855
[18] Wang, B. et al. A Comprehensive Survey on Shadow Removal from Document Images: Datasets, Methods, and Opportunities. Vicinagearth, 2025. https://doi.org/10.1007/s44336-024-00010-9
[19] Wang, J.; Li, X.; Yang, J. Stacked Conditional Generative Adversarial Networks for Jointly Learning Shadow Detection and Shadow Removal. IEEE/CVF Conference on Computer Vision and Pattern Recognition, 2018. https://doi.org/10.1109/CVPR.2018.00192
[20] Wu, Z. et al. Single-Image Specular Highlight Removal via Real-World Dataset Construction. IEEE Transactions on Multimedia, 2022. https://doi.org/10.1109/TMM.2021.3107688
[21] Jo, S. et al. S-LIGHT: Synthetic Dataset for the Separation of Diffuse and Specular Reflection Images. Sensors, 2024. https://doi.org/10.3390/s24072286
[22] Hsieh, C.-Y.; Ding, J.-J. ADSP: Advanced Dataset for Shadow Processing, Enabling Visible Occluders via Synthesizing Strategy. Asian Conference on Computer Vision, 2024. https://openaccess.thecvf.com/content/ACCV2024/html/Hsieh_ADSP_Advanced_Dataset_for_Shadow_Processing_enabling_visible_occluders_via_ACCV_2024_paper.html
[23] Liu, T. et al. Exposure Bracketing Techniques for Camera Document Image Enhancement. Applied Sciences, 2019. https://doi.org/10.3390/app9214529
[24] Bezmaternykh, P. V.; Ilin, D. A.; Nikolaev, D. P. U-Net-bin: Hacking the Document Image Binarization Contest. Computer Optics, 2019. https://doi.org/10.18287/2412-6179-2019-43-5-825-832
[25] Rim, J. et al. Real-World Blur Dataset for Learning and Benchmarking Deblurring Algorithms. European Conference on Computer Vision, 2020. https://graphics.postech.ac.kr/researches/RealBlur/
