# Evaluation of page detection in scenes captured by camera

## Abstract

Correctly locating a page in an image is a prerequisite for a camera-assisted drawing system to support paper-based activity, yet everyday scenes vary in lighting, occlusion, framing, background, and motion. Literature on photographed documents provides methods and datasets, but its criteria do not always transfer to an interactive task. This article proposes an evaluation that defines correct detection through region overlap and corner error without imposing a universal value. It organizes scene factors into qualitative levels, proposes a balanced design, and combines precision, recall, mean overlap, geometric error, and time to first detection. The protocol also addresses uncertain annotation, scenes without a reliable reference, and sensitivity analysis for criteria selected before data collection. Figures are planning diagrams, not results. The article contributes concepts, metrics, and a protocol for future studies. Since no empirical data are available, it makes no performance claim and leaves the results fields pending.

**Keywords:** page detection; photographed documents; computer vision; evaluation; uncontrolled scenes

## 1. Introduction

Locating the page in a scene captured by camera seems a simple task while the paper is isolated, flat, and fully visible. In everyday use, however, pages may appear partially, receive shadow, reflect light, occupy a small part of the image, or blend with textured backgrounds. An evaluation that counts only easy frames may suggest broad performance without testing the conditions that motivate its use. To compare camera-assisted drawing systems, it is necessary to define what counts as a page detected correctly and how the difficulty of the scene will be represented.

Page detection can be formulated as localization of a quadrilateral region, segmentation of a paper area, or identification of corners and contour. These formulations are not equivalent. A region may overlap the annotation and still present displaced corners; a corner estimate may be geometrically close but fail under partial occlusion; a late detection may be correct when it appears but of little use for the interactive task. Therefore, the question of "success" must combine localization, geometry, and time, without defining a universal threshold before considering the use.

Literature on photographed documents addresses perspective distortion, non-uniform illumination, shadows, curvature, blur, and complex backgrounds. Benchmarks of documents and scene images support comparison of methods, but may privilege specific document types or capture conditions. Segmentation work and overlap-based evaluation offer consolidated metrics, while rectification studies use corner error or the quality of the resulting image. These traditions form a methodological basis, but do not resolve how to balance scene factors and evaluate detection in a continuous interaction with paper.

The gap this article addresses is an implementation-independent evaluation protocol that defines correct page detection, represents scene factors explicitly, and associates complementary metrics. The proposed question is: **how to evaluate page localization in varied scenes, distinguishing spatial error, absence of detection, and delay until the first response?** Future research should separate geometric quality, coverage of conditions, and temporal availability, avoiding reducing everything to a single aggregate rate.

The article offers three contributions. First, it defines an operational notion of correct detection based on overlap and corner error, with criteria chosen before collection. Second, it organizes scene factors and qualitative levels to build a balanced evaluation without assuming that all factors have the same effect. Third, it proposes a set of metrics and an analysis that separates success, geometry, and time to first detection. None of these contributions asserts a result about a system that has already been measured.
 Sample selection also makes explicit whether the evaluation is per static image or per sequence, and whether the page must remain visible throughout the activity. This choice determines what "first detection" means and avoids comparing an isolated photograph to a continuous interaction as if they were the same problem.

Section 2 reviews detection and rectification of photographed documents, segmentation in natural scenes, and benchmark metrics. Section 3 presents definitions and the factor taxonomy. Section 4 describes scenes, annotation, success criteria, metrics, and analysis. Section 5 lists results to be filled in when data exist. Section 6 discusses possible interpretations; Section 7 delimits threats to validity; and Section 8 summarizes what is missing for empirical conclusions.

The population of interest need not be treated as "all pages". A project may delimit loose sheets, pages drawn in domestic environments, or specific conditions of use. This delimitation guides the factors and the choice of annotations. Broad terms such as "robust" or "works in the real world" do not replace the specification of which scenes were included, which were absent, and which uses motivate the comparison. The proposal emphasizes this point because the same metrics can support different conclusions when the target population changes.

## 2. Related work

### 2.1 Localization and rectification of photographed documents

Digitizing documents by camera combines page detection and correction of its geometry. Rectification works represent the sheet as a flat or nearly flat surface and seek to locate a bounding region before transforming the image into a frontal view [5–8]. Methods based on boundaries, local structures, and morphological operations address the relationship between contour and captured image [6, 7, 9]. These studies provide geometric and image concepts, but do not by themselves establish performance criteria for an interactive drawing scenario.

Methods for locating documents in photographed images often combine color, gradient, lines, edges, and shape hypotheses. Binarization competitions organize comparison of degraded documents, while studies of detection in smartphone videos address natural scenes and capture variation [11, 12, 20–22]. The factors considered vary with the problem. A method for printed documents may presuppose text and contrast that do not exist on a blank drawing sheet. The evaluation must therefore specify whether the annotated region corresponds to the physical sheet, the useful area, or another operational definition.

Rectification transforms the observed image toward a representation closer to the page seen from the front. Rectification metrics may measure corner error, correspondence between lines, or the visual quality afterwards. A good contour overlap does not guarantee that each corner is accurate, and a corner difference may have a larger effect in one region of the sheet than in another. For this article, rectification is related context; the central question is locating the page. It is not described how a system performs this operation, nor is it assumed that the evaluation must expose its internal representation.

### 2.2 Segmentation and detection in natural scenes

Segmentation seeks to separate regions of interest from the background, while detection may produce a box, a polygon, or a mask. Evaluation work in computer vision stresses that the choice of representation affects the metric. A bounding box may ignore the quadrilateral shape of the page; a mask may evaluate detailed contour but require more costly annotation. For an approximately flat sheet, the quadrilateral region and its corners provide complementary descriptions. The evaluation can compute area overlap and geometric error, keeping the definition of success independent of any architecture.

The overlap between prediction and annotation is often summarized by intersection over union, known as Intersection over Union (IoU), or by the Jaccard index in document protocols [1, 2]. This metric compares shared area with the area covered by both regions. A higher IoU indicates greater overlap under that representation, but by itself does not establish whether the error matters for the use. An IoU-based success rate requires a minimum value chosen before the evaluation. Varying this criterion in a sensitivity analysis shows how conclusions depend on the definition, instead of retrospectively selecting the most favorable value.

Detection benchmarks in natural scenes promote shared protocols, data splits, and comparable metrics. Detection benchmarks have consolidated evaluation practices by precision, recall, and overlap, although generic objects do not necessarily correspond to sheets. Collections of camera-captured documents, such as SmartDoc and DocUNet, approach the question and include capture variations or deformation [1, 3, 4]. No collection replaces validation for a particular task. The composition of the sample must cover the space of interest and declare its limits.

### 2.3 Benchmarks and evaluation metrics

Precision and recall respond to different aspects. Precision indicates what fraction of the declared detections corresponds to valid pages under the adopted criterion; recall indicates what fraction of the annotated pages was found. Both may be affected by the matching procedure between detections and annotations. If there is more than one candidate region or several pages in the scene, the matching rules must be described. An image-level aggregate metric may also treat scenes with one page and scenes with several plausible regions differently.

Corner error measures the distance between predicted and annotated corners, in pixels or normalized by an image dimension. Error in pixels depends on capture resolution; a normalized measure improves comparison across sizes but may hide the absolute impact in an application. Reporting both may be appropriate when resolution is part of the design. Time to first detection measures the interval between the start of a valid condition and the first response that satisfies the success definition. This temporal measure complements geometry, but depends on the observation cadence and on the persistence rule for responses.

Binarization competitions document protocols and metrics for comparing document images, but should not be confused with page-boundary benchmarks [20–22]. The literature also discusses annotation quality and disagreement between evaluators. The physical edge of a page may be ambiguous when there are shadows, folds, or occlusion. An annotation protocol must declare how corners are identified in partial cases, whether evaluators work independently, and how disagreements are resolved. The benchmark must record which scenes were excluded and why. A metric computed over unstable labels should not be interpreted as an accurate measure of behavior.

The gap that remains is a protocol for evaluating page detection under conditions relevant to camera-assisted drawing, combining overlap, geometry, factor coverage, and time to first detection. The proposal of this article uses benchmark practices as methodological reference, but does not copy collections or presume that its domain is interchangeable with theirs. The contribution is to make annotation and success choices explicit, allowing future studies to compare conditions without hiding dependence on criteria.

Segmentation results also depend on the form of annotation and the granularity of the evaluated region. A detailed mask may penalize small contour differences that do not alter the useful localization, while a box may ignore important deformation at the corners. Therefore, the choice of representation must be consistent with the question and presented together with the results. If an existing benchmark is reused, the study must declare which classes, splits, or images were used and why that subset corresponds to the defined population.

## 3. Problem framing

In this article, a page is the physical sheet that constitutes the region of interest in the scene. The reference annotation is a polygon defined by the observable edge of the sheet, together with its corners when they can be identified. In situations with occlusion, shadow, or fold, the annotator follows a common instruction and marks the uncertainty, instead of inventing an invisible edge. A scene may be classified as evaluable, partially evaluable, or without a reliable reference; this classification must be determined without consulting the system's output.

A detection is an observable report of a candidate region associated with the page. To compare detection and reference, the intersection over union between the polygonal areas is computed. The minimum overlap criterion that defines success must be chosen before the results are examined. The article does not fix a value, since its adequacy depends on how the page will be used. A sensitivity analysis can show whether the conclusion changes under justified alternative criteria, without selecting only the one that maximizes performance.

Detection geometry is evaluated separately by corner error. For each paired corner, the distance between the estimated position and the reference is measured. The error may be reported in pixels and normalized by an image dimension, provided the normalization is declared. When the page is partially hidden and a corner cannot be annotated with confidence, the evaluation reports that absence and does not assign zero error. The region may still be compared if there is a partial annotation with explicit rules, but these cases must be analyzed separately.

The temporal dimension distinguishes finding a page from finding it in time to support the activity. Time to first detection is the interval between the first scene in which the page meets the inclusion criteria and the first response that satisfies the predefined success criterion. This metric does not claim that the response remains stable after the first event. If continuity is relevant, it must be described by its own persistence or failure measures, without being confused with initial detection.

The success definition also distinguishes a page from similar regions in the background. A white sheet on a light table may have a barely visible boundary; a printed rectangle may visually compete with the edge; a nearby rectangular area may receive a false detection. Such cases require annotating the physical object of interest and recording plausible alternatives. The team must not choose the reference region from the output it wishes to evaluate. A common instruction, reviewed before analysis, reduces this risk, although it does not eliminate it.

Finally, the metrics characterize different properties of the decision to localize. Overlap summarizes area, corner error summarizes geometry, precision and recall summarize correspondence with references, and time describes temporal availability. There is no reason to expect one measure to represent all the others. A fair comparison presents disaggregated results and explains which dimension supports each conclusion. This separation is especially important when a task requires continuity of the activity and not merely later recognition of the image.

Scene factors are controllable or recordable properties that may alter visibility and geometry. Table 1 organizes them by type and by qualitative levels. The descriptions "lower", "intermediate", and "higher" indicate the planned ordering within a factor, not universal physical values. The intensity of a shadow, for example, is not directly comparable to the fraction of page covered. The levels must be defined observably in the protocol and photographed or described to allow auditing.

**Table 1.** Scene factors and qualitative levels proposed for a balanced evaluation, making explicit variations in lighting, occlusion, framing, background, page appearance, distance, and motion, organized into qualitative coverage levels.

| Factor | Possible qualitative levels | How to define in the protocol | Risk of confusion |
|---|---|---|---|
| Lighting | uniform; localized shadow; glare | Describe the distribution and position of the observable light | May be confused with the color and texture of the paper. |
| Occlusion | absent; partial; extensive | Record the visible region and the covered part | Corner annotation may become uncertain. |
| Framing | central; near the edge; partially outside the scene | Describe the relative position of the sheet in the image | May vary together with apparent scale. |
| Background | simple; textured; with nearby objects | Categorize the elements around the sheet | Contrast may change with the background color. |
| Page appearance | light; colored; with marks or fold | Record the visible color, content, and deformation | Marks may be confused with the edge. |
| Distance | near; intermediate; far | Define observable categories by capture configuration | Apparent size and focus also change. |
| Motion | still; small movement; continuous movement | Record the temporal condition during capture | Blur and framing changes may coexist. |
| Focus and sharpness | sharp; slightly blurred; blurred | Define by independent inspection, not by detection | Blur may result from motion or from focus. |

The problem framing also separates absence of detection, incorrect detection, and late correct detection. Absence is a valid scene without a corresponding response during the evaluated period. Incorrect detection occurs when the reported region does not correspond to the reference page according to the established criterion. Late detection satisfies the geometric criterion but exceeds the observation window defined for the task. The window must be justified by the protocol, not chosen after knowing the performance.

The factor figure presents schematic examples without suggesting real outputs. The matrix in Figure 2 shows that a balanced evaluation considers crossings of conditions, even though the complete combination may be too large. The selection of subsets must preserve coverage and explain which interactions between factors will be evaluated. Figure 3 provides only one expected form for relating perturbation and performance; no trend is attributed to the system.

## 4. Proposed evaluation protocol

The study begins by defining the population of scenes and the unit of analysis. A scene corresponds to an annotated capture condition, and a sequence corresponds to related observations during a task. The sample must include scenes planned to cover the factors in Table 1, in addition to natural variation that is relevant to the question. The team documents the origin, conditions, and usage restrictions of the images. If scenes involve people or private space, consent and protection of identity are defined before collection.

Sample construction must avoid a difficult condition always appearing together with another. For example, if all scenes with shadow also have the page partially outside the framing, their effects cannot be separated. A complete factorial design may be unfeasible; in that case, a balanced plan selects combinations that cover each factor and the priority interactions. The selection is recorded before execution. The report presents which combinations were included and which were left out, without treating partial coverage as full coverage.

Reference annotation is produced by people who do not see the evaluated outputs, when this is practicable. The manual defines edge, corners, occlusion, and ambiguous cases. A portion of the scenes receives independent annotation by more than one person to estimate disagreement. The study reports the adjudication procedure, the way uncertainty is represented, and the number of cases without a reliable reference after collection. If a condition physically alters the sheet, such as a fold or a crease, the annotation follows the visible edge without presuming a perfectly flat shape.

**Definition of success.** The primary rule combines region and geometry: the detection must satisfy the previously defined overlap criterion and remain within the geometric tolerance established for valid corners. The study fixes these criteria before analyzing the evaluation set, with a justification tied to the use. Since there is no universal value, results of sensitivity to alternative criteria are presented in case the conclusion depends on them. The article does not determine an overlap number or a tolerance in pixels.

The correspondence between detections and annotated pages is defined for scenes with one or several candidate regions. The matching method, the policy for repeated detections, and the way missing pages are handled are recorded. A page predicted more than once must not inflate recall; detections on the background must not disappear from the precision evaluation. For a scene without an evaluable page, the protocol clarifies whether it measures a false positive, is excluded from the main analysis, or forms a separate analysis.

The team measures precision, recall, mean overlap, corner error, and time to first detection. Table 2 presents definitions and limits. Precision and recall use counts derived from the matching and the success criterion. Mean overlap summarizes matched regions and must be accompanied by its distribution, since the mean may hide bad cases. Corner error is reported per scene and per corner when possible. Time to detection uses the sequence and the starting mark specified. Uncertainty intervals are estimated with a method compatible with the sampling unit, without treating frames from the same session as independent observations.

**Table 2.** Metrics to characterize page detection, with definitions independent of numerical thresholds; the team must fix success criteria before collection and report uncertainty.

| Metric | Definition | Unit or aggregation | Interpretive limit |
|---|---|---|---|
| Precision | Correct detections divided by reported detections | Proportion per scene or condition | Depends on the criterion and matching adopted. |
| Recall | Pages correctly detected divided by evaluable annotated pages | Proportion per scene or condition | Does not summarize delay or geometric quality. |
| Mean IoU | Area of intersection divided by area of union between detected and annotated region | Proportion per matched case | The mean may hide tails and failure cases. |
| Corner error | Distance between corresponding corners of detection and reference | Pixels and, if justified, a normalized measure | Sensitive to resolution and annotation uncertainty. |
| Time to first detection | Time from the first valid scene to a response that meets the criterion | Time per sequence | Depends on temporal sampling and the observation window. |
| Localization failure | Absence of the correct region or region outside the criterion | Count and proportion per factor | Must distinguish absence, incorrectness, and delay. |

The matrix and the figures help communicate the structure of the protocol before any result. Figure 1 presents factors of the scene schematically; Figure 2 illustrates the grid of factors and levels; Figure 3 shows a generic curve without values. These elements do not describe the internal configuration of the system. They are planning and communication instruments of the study.

![](figures/02-fatores-cena.svg)

**Figure 1.** Conceptual panels of scenes with distinct light, occlusion, and framing. The labels indicate factors to vary, not images of participants or outputs of the evaluated system; author's own work.

![](figures/02-matriz-fatores.svg)

**Figure 2.** Conceptual matrix of factors by qualitative levels, intended to guide coverage of conditions. The cells are empty and do not represent counts, results, or measured intensities; author's own work.

![](figures/02-curva-deteccao.svg)

**Figure 3.** Illustrative curve between scene perturbation and detection performance, with axes without values. The expected form is not a result and does not anticipate an empirical trend; author's own work.

The analysis begins with statistics by factor and level, and then examines previously selected interactions. The team presents values per scene and aggregates, distribution and uncertainty, as well as failures and cases without reliable annotation. The sensitivity analysis shows whether the pattern depends on the overlap criterion or on the corner tolerance. A comparison with a generic baseline may help contextualize the protocol, but must use the same data, annotations, and conditions. The label "baseline" describes a comparison reference, not a specific implementation.

Time to first detection is analyzed separately from precision and geometry. A fast but incorrect detection is not a success, just as a correct detection that arrives late may be inadequate for a continuous task. The observation window and the policy for sequences without detection are pre-specified. If the temporal distribution is asymmetric, robust summaries and the tail are reported. Frames missing from the external record are treated as an instrument failure, not as an automatic absence of detection.

The validity of the protocol depends on coverage, annotation, and the clarity of definitions. Data review checks whether factors were balanced and whether categories are usable. The team keeps a record of changes to the plan, explains deviations, and avoids altering criteria after inspecting results. The release of materials, descriptions, and analytic code must respect licenses and privacy, allowing auditing to the extent possible.

A baseline must be chosen for its methodological relevance, not for convenience or expected result. It may represent a generic geometric rule or a published practice, provided its application uses exactly the same scenes and labels. The comparison must not reveal details of a proprietary system or turn a benchmark article into a claim of equivalence between tasks. If the procedures differ, the text must explain why the comparison remains informative.

To reduce order effects, the conditions may be presented in random sequence or in balanced blocks, as equipment and logistics allow. The team records restarts, losses of the external recording, and conditions that had to be repeated. The resampling unit for uncertainty intervals must respect the dependence between images of the same sequence. Treating all correlated frames as independent observations would artificially narrow the uncertainty and make the evidence appear stronger than it is.

## 5. Structure of the results

The results should begin with a description of the scene set and the coverage of factors. The composition table will show how many conditions were included at each level after collection, which combinations were not observed, and how many scenes remained without reliable geometric reference. No total is anticipated in this article. The section will present the annotation procedure, the observed disagreement among evaluators, and the exclusions, distinguishing data limitations from detection failures.

For each factor, precision, recall, overlap, corner error, and time to first detection will be reported. The metrics will be presented by level and in aggregates, with distribution and uncertainty appropriate to the sampling unit. A generic baseline, if included, will be evaluated with the same scenes and references. Results under alternative overlap criteria will be kept visible to show the sensitivity of the conclusions, and not to retrospectively choose a favorable criterion.

The conceptual figures of this proposal do not represent data. The curve in Figure 3 should be replaced by a visualization derived from observations once collection occurs, identifying the conditions and the aggregation method. Table 3 marks the fields awaiting measurement. Cells without observation will be identified as [PENDING-DATA], and the absence of an estimate will not be presented as null or perfect performance.

**Table 3.** Planned result fields for a future application, separating scene composition, geometric quality, detection, delay, and annotation uncertainty; all measures remain pending until collection.

| Field | Future result |
|---|---|
| Coverage of factors and combinations | [PENDING-DATA] |
| Precision and recall by condition | [PENDING-DATA] |
| Mean overlap and distribution | [PENDING-DATA] |
| Corner error and annotation uncertainty | [PENDING-DATA] |
| Time to first detection | [PENDING-DATA] |
| Comparison with baseline | [PENDING-DATA] |

## 6. Discussion

If detection remains correct under varied conditions, the result will support a claim restricted to the sample and to the criteria evaluated. It will not demonstrate universal robustness nor eliminate the need for tests in absent contexts. The interpretation will depend on factor coverage, the reliability of annotations, and the presence of interactions between conditions. Consistent performance in illuminated and well-framed scenes does not authorize generalization to shadow, occlusion, or motion if these conditions were not included.

If overlap is high but corner error is also relevant, the metrics are responding to different granularities. The region as a whole may coincide substantially while small localized displacements remain. This difference may matter for an application that depends on geometric alignment, but matter less when it is enough to detect the presence of the page. The intended use should guide interpretation; none of the measures should be treated as an automatic substitute for the other.

If precision and recall diverge, the system may produce few incorrect detections and leave pages unlocated, or find many pages at the cost of mistaken candidates. Presenting them together makes this trade-off observable. A single composite measure could hide the difference. The analysis should also report the types of scene associated with failures and check whether the pattern stems from uneven coverage, uncertain annotation, or systematic behavior.

If the time to first detection increases in some conditions, correct geometric detection may still arrive late for a continuous interaction. This result would relate to studies of document processing in video, which address updating during capture, but would not be directly comparable without aligning definitions of start and success. A late response and an absence of response are distinct outcomes. The time window and the required persistence must be established before collection.

If the conclusion depends strongly on the overlap criterion, the study should highlight this sensitivity. The result is not a reason to select the value that yields the highest accuracy; it indicates that the definition of success needs justification tied to the use. Sensitivity analysis and corner error help separate the operational decision from the observed evidence. This recommendation follows the practice of benchmarks that make criteria explicit, while recognizing that different document protocols have distinct purposes.

The protocol approaches research on rectification, segmentation, and evaluation of photographed documents [1–15, 20–25]. These lines of work show factors such as shadow, low illumination, blur, deformation, and occlusion, along with solutions with varied objectives. The article does not compare specific methods nor claim superiority. Its contribution is to propose an implementation-independent evaluation structure that exposes how sample, success criterion, and metric shape the conclusions.

## 7. Limitations and threats to validity

Construct validity depends on the correspondence between the definition of page and the object of interest. The edge may be ambiguous under shadow, fold, low contrast, or occlusion. An uncertain corner annotation may introduce error into the metric used to evaluate the system itself. The protocol recommends recording uncertainty and separating scenes without reliable reference, but this exclusion may reduce the representation of the most difficult conditions. The team must show how many cases were excluded and for what reason after collection.

Internal validity is threatened by factors that vary together. Distance changes apparent scale; motion may generate blur; illumination may alter contrast; the position of background and sheet may change simultaneously. A balanced design reduces confounding, but incomplete combinations leave interactions unobserved. The study must not interpret correlations between factor and failure as causal effects when it has not controlled concurrent conditions. Analyses of one condition at a time do not necessarily capture real-world interactions.

Measurement validity depends on image resolution, the quality of temporal recording, and the matching rules. IoU depends on the annotated region and on the success criterion. Corner error in pixels varies with image size, while a normalized measure depends on the dimension chosen. Precision and recall change with the policy for multiple detections. The report must document these choices so that results from different sources do not appear comparable when they use incompatible definitions.

External validity is limited by the selection of pages, backgrounds, devices, physical conditions, and activities. A set with specific drawings or materials may not represent white, colored, folded, or nearby-object pages. Document photograph models found in the literature may not cover the needs of continuous interaction. The diversity of scenes must be described without claiming representativeness of "real use" based on convenience or on a few conditions.

Data validity involves privacy, consent, licensing, and annotation quality. Images may include people or written content. Sharing must respect permissions and reduce identifiable information when necessary. Restrictions must be described, since unavailability of data reduces independent auditing. This article does not present a benchmark or collected data; the adequacy of the proposed factors itself still needs to be examined in a pilot.

## 8. Conclusion

This article proposed evaluating page detection in scenes captured by camera with complementary metrics of precision, recall, overlap, corner error, and time to first detection. It also organized scene factors into qualitative levels and described an annotation, balancing, and sensitivity analysis protocol. The notion of correct detection was defined without imposing a universal numerical criterion.

The proposal does not report the performance of any existing system. A future application will need to justify criteria, gather scenes with adequate coverage, record annotation uncertainty, and fill in the pending fields. Conclusions will need to remain limited to the conditions observed and to the uses that motivated the criteria. Without data and independent review, the contribution remains methodological.
 The choice of factors may be revised after a pilot, provided the changes occur before the main collection and are documented. The study should also preserve the difference between detected region, geometric quality, and response time, since each dimension answers a distinct question.

## Statements

- Use of generative AI: text drafted with the support of generative AI, with review and responsibility of the authors; references checked by DOI or bibliographic page.
- Data: this article does not present experimental data; future images must respect privacy, license, and consent.
- Code: there is no implementation of evaluation or result analysis associated with this manuscript.
- Conflict of interest: the authors must declare relevant conflicts before submission.
- Ethics: future studies involving people or identifiable content must obtain ethical approval and applicable consent.
- Author contributions: individual contributions must be described in the submitted version.

## References

[1] Burie, J.-C.; Chazalon, J.; Coustaty, M. et al. ICDAR2015 Competition on Smartphone Document Capture and OCR (SmartDoc). 2015 13th International Conference on Document Analysis and Recognition, 2015, 1161–1165. https://doi.org/10.1109/ICDAR.2015.7333943
[2] Zhukovsky, A.; Nikolaev, D.; Arlazarov, V. et al. Segments Graph-Based Approach for Document Capture in a Smartphone Video Stream. 2017 14th IAPR International Conference on Document Analysis and Recognition, 2017, 337–342. https://doi.org/10.1109/ICDAR.2017.63
[3] Ma, K.; Shu, Z.; Bai, X.; Wang, J.; Samaras, D. DocUNet: Document Image Unwarping via a Stacked U-Net. Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition, 2018, 4700–4709. https://doi.org/10.1109/CVPR.2018.00494
[4] Das, S.; Ma, K.; Shu, Z.; Samaras, D.; Shilkrot, R. DewarpNet: Single-Image Document Unwarping With Stacked 3D and 2D Regression Networks. Proceedings of the IEEE/CVF International Conference on Computer Vision, 2019. https://doi.org/10.1109/ICCV.2019.00022
[5] Tsoi, Y. C.; Brown, M. S. Multi-view document rectification using boundary. Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition, 2007. https://doi.org/10.1109/CVPR.2007.383251
[6] Lu, S.; Chen, B. M.; Ko, C. C. Perspective rectification of document images using fuzzy set and morphological operations. Image and Vision Computing, 23(6), 2005, 541–553. https://doi.org/10.1016/j.imavis.2005.01.003
[7] Lu, S.; Chen, B. M.; Ko, C. C. A partition approach for the restoration of camera images of planar and curled document. Image and Vision Computing, 24(8), 2006, 837–848. https://doi.org/10.1016/j.imavis.2006.02.008
[8] Liang, J.; DeMenthon, D.; Doermann, D. S. Geometric Rectification of Camera-Captured Document Images. IEEE Transactions on Pattern Analysis and Machine Intelligence, 30(4), 2008, 591–605. https://doi.org/10.1109/TPAMI.2007.70724
[9] Zhu, Y.; Dai, R.; Xiao, B.; Wang, C. Perspective rectification of camera-based document images using local linear structure. Proceedings of the ACM Symposium on Applied Computing, 2008, 451–452. https://doi.org/10.1145/1363686.1363797
[10] Koo, H. I.; Cho, N. I. Rectification of Figures and Photos in Document Images Using Bounding Box Interface. Proceedings of the IEEE Computer Society Conference on Computer Vision and Pattern Recognition, 2010, 3121–3128. https://doi.org/10.1109/CVPR.2010.5540071
[11] Puybareau, É.; Géraud, T. Real-Time Document Detection in Smartphone Videos. Proceedings of the IEEE International Conference on Image Processing, 2018, 1498–1502. https://doi.org/10.1109/ICIP.2018.8451533
[12] Vũ Ngọc, M. Ô.; Fabrizio, J.; Géraud, T. Document detection in videos captured by smartphones using a saliency-based method. Proceedings of the International Conference on Document Analysis and Recognition Workshops, 2019. https://doi.org/10.1109/ICDARW.2019.30059
[13] Tropin, D. V.; Ilyuhin, S. A.; Nikolaev, D. P.; Arlazarov, V. V. Approach for Document Detection by Contours and Contrasts. Proceedings of the International Conference on Pattern Recognition, 2021, 9689–9695. https://doi.org/10.1109/ICPR48806.2021.9413271
[14] Pan, R.; Zhu, A. Multi-document detection via corner localization and association. Neurocomputing, 466, 2021, 37–48. https://doi.org/10.1016/j.neucom.2021.09.033
[15] Tropin, D. V.; Ershov, A. M.; Nikolaev, D. P.; Arlazarov, V. V. Advanced Hough-based method for on-device document localization. Computer Optics, 45(5), 2021, 702–712. https://doi.org/10.18287/2412-6179-CO-895
[16] Lins, R. D. Document Image Binarization Platform (DIB Platform), v.1. TC-11 dataset and platform, 2017. https://tc11.cvc.uab.es/datasets/DIB%20Platform_1
[17] Alqudah, M. K.; Bin Nasrudin, M. F.; Bataineh, B. et al. Investigation of binarization techniques for unevenly illuminated document images acquired via handheld cameras. 2015 2nd International Conference on Computer, Communications, and Control Technology, 2015. https://doi.org/10.1109/I4CT.2015.7219634
[18] Chaves, G. P.; Vieira, T.; Silva, G. de F. P. e; Lins, R. D.; Simske, S. J. A Quality, Size and Time Assessment of the Binarization of Documents Photographed by Smartphones. Journal of Imaging, 9(2), 2023, 41. https://doi.org/10.3390/jimaging9020041
[19] Wang, B.; Chen, C. L. P. Local Water-Filling Algorithm for Shadow Detection and Removal of Document Images. Sensors, 20(23), 2020, 6929. https://doi.org/10.3390/s20236929
[20] Gatos, B.; Ntirogiannis, K.; Pratikakis, I. DIBCO 2009: document image binarization contest. International Journal on Document Analysis and Recognition, 14, 2011, 35–44. https://doi.org/10.1007/s10032-010-0115-7
[21] Pratikakis, I.; Gatos, B.; Ntirogiannis, K. ICDAR 2011 Document Image Binarization Contest (DIBCO 2011). Proceedings of the International Conference on Document Analysis and Recognition, 2011, 1506–1510. https://doi.org/10.1109/ICDAR.2011.299
[22] Pratikakis, I.; Zagoris, K.; Barlas, G.; Gatos, B. ICDAR2017 Competition on Document Image Binarization (DIBCO 2017). Proceedings of the International Conference on Document Analysis and Recognition, 2017. https://doi.org/10.1109/ICDAR.2017.228
[23] Lopes Junior, C. A. M.; Neves Junior, R. B. das; Bezerra, B. L. D. et al. ICDAR 2021 Competition on Components Segmentation Task of Document Photos. Proceedings of the International Conference on Document Analysis and Recognition, 2021, 678–692. https://doi.org/10.1007/978-3-030-86337-1_45
[24] Li, H.; Wu, X.; Chen, Q.; Xiang, Q. Foreground and Text-Lines Aware Document Image Rectification. Proceedings of the IEEE/CVF International Conference on Computer Vision, 2023, 19574–19583. https://doi.org/10.1109/ICCV51070.2023.01793
[25] Sun, R.; Wang, S.; Ji, L.; Wang, Z. Rectification of camera-captured document images with multi-column layouts and non-textual objects. Electronics Letters, 54(8), 2018, 502–503. https://doi.org/10.1049/el.2018.0470
