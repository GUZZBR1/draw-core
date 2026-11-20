# Geometric stability of sheets in camera-assisted drawing interaction

## Abstract

Changes in page pose alter its image position and may displace a drawing representation relative to the paper. Evaluating “spatial stability” requires separating angle, distance, and motion, as well as distinguishing physical error from error relative to page size. This article proposes a protocol to measure these quantities in scenes captured by a camera-assisted drawing system without describing how pose is estimated. The proposal defines stroke displacement, absolute error in millimeters, error normalized by page width, temporal drift, and correspondence failures. A grid crosses orientations, distances, and stationary or moving states, while a generic classical geometric baseline provides comparison under the same conditions. The protocol includes an independent reference, sequence-level analysis, and instrumental uncertainty. Figures present conceptual diagrams only; the curve contains no values. Since no measurements are available, the article makes no stability claim about the system and leaves results pending until an empirical evaluation.

**Keywords:** projective geometry; homography; camera calibration; planar tracking; geometric error

## 1. Introduction

The sheet of paper changes position while the person writes or draws. It may rotate, move closer to or farther from the camera, and shift during capture. The ink that is drawn also occupies positions relative to the sheet that one wishes to preserve. A geometric evaluation must separate the physical movement of the paper from an undesired change in the observed representation. Without this distinction, “stability” may mean that the page remained still, that the stroke appeared stable in the image, or that its relative position was preserved; these meanings are not equivalent.

The geometry of planar scenes offers concepts for describing the relation between a surface and its image. Work on calibration, document rectification, and planar tracking examines how position and orientation affect measurements in images. However, an applied evaluation requires defining which poses matter, which displacement is considered error, and how to compare stationary and moving conditions. An absolute value in pixels is not comparable across images with different resolutions. A measurement in millimeters may be interpretable in the space of the sheet, while error normalized by width helps compare different paper scales.

The gap addressed by this article is an operational formulation of spatial stability for a sheet used during camera-assisted drawing. The proposed question is: **how can the geometric error of the stroke relative to the sheet be characterized under different angles, distances, and motion states?** The objective is to structure a protocol with an independent reference and a generic classical geometric baseline, without describing how the evaluated system estimates pose or maintains correspondence.

The article offers three contributions. First, it defines quantities for sheet pose, stroke displacement, and absolute error and error relative to sheet width. Second, it proposes a grid of conditions that crosses orientation, distance, and motion. Third, it specifies metrics and a comparison with a generic baseline under identical conditions. These are contributions to a future study; no geometric result is presented.

Section 2 reviews projective geometry, calibration, rectification, and planar tracking. Section 3 defines stability and presents quantities and units. Section 4 proposes scenes, conditions, metrics, analysis, and comparison. Section 5 lists pending results. Section 6 discusses possible interpretations; Section 7 addresses threats to validity; and Section 8 summarizes the evidence that is still missing.

The protocol assumes that the paper has physical dimensions that can be identified for the purpose of the evaluation. If the sheet is folded or curved, its geometry is no longer well described by an ideal plane. Such situations may be excluded from the scope, grouped as an additional condition, or evaluated with an appropriate reference, but the decision must be explicit. Stability also depends on how much error matters for the task. A displacement may be tolerable for free-form annotation and unacceptable for a precise overlay. The proposal separates measurement from judgment of usefulness, leaving the study to justify margins based on use and instrumental uncertainty.

An evaluation need not require the paper to remain in an ideal pose. Movement is part of use and should be represented as a condition, not automatically discarded as noise. The question is whether the relation between stroke and sheet remains within a variation that is justifiable for the stated purpose. That purpose may favor preservation of position, shape, continuity, or legibility. The protocol makes this choice explicit before collection and avoids interpreting a single measure as complete geometric quality.

A central methodological decision is to choose the frame of reference of the claim. If the study asks where the stroke appears in the camera frame, the measurement belongs to the image plane. If it asks whether the stroke remains over the same region of the paper, the sheet is the frame of comparison. A third question may evaluate fidelity after digitizing the final drawing. All three questions may be useful, but they answer different objectives. The article concentrates on the second and reports physical units when the reference allows. This delimitation prevents the sheet's own movement from being counted as error, or an error relative to the paper from disappearing within a global image measurement.

## 2. Related work

### 2.1 Projective geometry and planar rectification

Projective geometry describes relations between coordinates in planes and their projections in images. The homography is a common mathematical representation for projective relations between planes, used in document rectification, panoramas, and surface alignment. Hartley and Zisserman systematize concepts and problems of geometric computer vision [1–4]; calibration texts explain how camera properties affect measurement and reconstruction. These foundations help define the pose and the transformation between reference frames, but the proposal does not assume a specific internal transformation for the evaluated system.

Rectification of photographed documents focuses on recovering a view of the page that facilitates reading or later processing. Work by Liang, DeMenthon, and Doermann studies geometric rectification of camera-captured documents [11, 12]. Tsoi and Brown use boundaries in multiple views to rectify documents, and other studies address flat and curved pages, perspective distortions, and local structures [13, 14, 21–23]. These methods illustrate that visible boundaries and the shape of the paper affect the estimated geometry. Their output objective may differ from stroke stability in continuous interaction, so rectification metrics are not automatically metrics of drawing preservation.

The document literature also highlights difficulty under shadows, non-uniform illumination, low contrast, and deformation. A sheet that looks flat for reading may move enough to influence stroke alignment. The evaluation must define whether it considers only static pose or the trajectory over time. This article treats both situations as conditions, keeping instantaneous geometry and temporal stability distinct.

### 2.2 Camera calibration and plane tracking

Camera calibration relates measurements in the image to properties of the projection and may include intrinsic parameters or the pose relative to the scene. Zhang describes a calibration method based on observations of a planar pattern in multiple orientations; other approaches use known geometries and lens constraints [5–10]. These lines of work are relevant for defining unit and uncertainty, but the proposal does not specify how the system estimates pose or which internal references it uses. The protocol measures the observable output and compares it with a separate experimental reference.

Planar tracking studies the maintenance of a surface's correspondence along a sequence. Work on multi-view document reconstruction, alignment, and plane tracking considers changes of scale, perspective, occlusion, and motion [15, 18, 20]. The geometric stability of a sheet is related to these problems, but the unit of interest here is the position of the stroke relative to the sheet, not the reconstruction of the whole scene. This scoping guides the choice of metrics and reduces the temptation to disclose implementation details.

Temporal stability and geometric accuracy are also not synonyms. An estimate may oscillate little but maintain a constant offset; another may be correct on average and vary widely from frame to frame. For this reason, the tracking literature motivates reporting error, dispersion, and failures, not only an average measure [4, 6, 22]. The pose trajectory may also be compared with the physical movement measured externally, when the equipment allows a reference with known uncertainty.

### 2.3 Geometric evaluation in captured documents

Benchmarks of camera-captured documents evaluate rectification, localization, or image quality under varied conditions [16, 17, 19]. The metric may consider distance between corners, alignment error, visual similarity, or OCR quality. The choice depends on the task: a small error at a corner may alter the reading of a region, while a global similarity measure may hide localized distortion. For drawing, the comparison must focus on the relation between the digital stroke and the physical page.

Tracking and rectification may also be evaluated in sequence, reporting per-frame errors, tracking failures, and recovery after occlusion. Sequence-level evaluation should not treat consecutive frames as independent observations. Temporal dependence reduces the effective information and affects uncertainty intervals. A cumulative metric may describe drift over the session, while instantaneous errors describe point discrepancies.

The generic classical baseline serves as a reference for interpreting gains or losses under identical conditions. Comparisons of geometric and calibration error also emphasize the need to declare the metric and the uncertainty [3, 4]. Its function is to establish a reproducible contrast with a traditional geometric practice, not to claim that a specific method is superior. It must receive the same scenes, annotations, and criteria and have its own failures reported. The baseline configuration will be described only enough to reproduce its evaluation, without exposing the implementation of the evaluated system.

The gap remains in the joint definition of pose, stroke displacement, and error normalized by sheet scale for an evaluation protocol under motion. This article brings together projective geometry, calibration, and tracking, but treats stability as an observable, task-oriented relation. The proposal does not claim a new geometric estimator. It organizes quantities, conditions, and comparisons that allow this relation to be tested empirically.

The need for an independent reference appears in several areas of computer vision. Reprojection error, correspondence error, and absolute geometric error quantify different aspects. A calibration may appear consistent under one criterion and still produce uncertainty in a downstream task. For this reason, the proposal states what each metric measures and does not use a single indicator as proof of correctness. The baseline and the evaluated method are judged against the same physical reference, with uncertainty reported.

The calibration and geometric vision literature also distinguishes measurement uncertainty from systematic error. A wide uncertainty may make two methods indistinguishable, while a consistent bias may be correctable but still relevant. The protocol does not presuppose that any reference method is exact. Instead, it requires the reference to report its precision and the comparison to account for that limit. When this information is not available, results will be described as approximations and not as exact physical error.

## 3. Problem framing

Sheet pose is the spatial configuration that describes its orientation and position relative to the camera during an observation. For this protocol, pose is organized by angle, distance, and motion. Angle describes the tilt of the sheet relative to the reference frontal orientation. Distance describes the separation between the camera and the paper surface, or a category of apparent scale when the physical distance cannot be measured precisely. Motion describes whether the sheet is stationary, moving slowly, or in continuous motion during the observation. These dimensions are recorded externally; the article does not describe how the system estimates them.

Stroke displacement is the difference in position between the corresponding location on the physical sheet and the observed representation. The reference may be obtained from an independent scan or from synchronized manual annotation, provided that the method preserves point identity and the uncertainty is documented. The article does not prescribe marks or points used internally by the system. The experimental reference is separate from the output to be evaluated and serves only to quantify the discrepancy.

Absolute error is the distance, in millimeters on the sheet surface, between the expected position of the stroke and the compared position. Error relative to sheet width normalizes this distance by the physical width of the page. If eᵢ is the absolute error of an observation and W the width of the sheet, the relative error can be written as rᵢ = eᵢ/W. This ratio facilitates comparison between sheets of different dimensions, but does not replace the absolute error: the same fraction may correspond to different physical displacements.

Spatial stability includes both mean deviation and temporal variation. Geometric bias is a persistent difference in one direction; dispersion describes the variation among observations. Drift is the accumulated change over time, which may be presented as an error trajectory or as the difference between start and end. Observation failure occurs when there is no reliable correspondence between the physical reference and the output for part of the sequence. These events must not be converted into zero error nor omitted without explanation.

Table 1 presents quantities and units. Angle may be reported in degrees, distance in millimeters or by apparent-scale classes, displacement and error in millimeters, and relative error as a dimensionless ratio. The definition of a unit presupposes a physical reference or a normalization procedure. If the sheet width is not known, the ratio cannot be computed reliably. The report distinguishes direct measurements, external estimates, and ordinal categories.

**Table 1.** Geometric quantities of the sheet and the stroke, with definitions, units, and interpretations; the table separates pose, displacement, absolute error, error relative to width, and observation failure.

| Quantity | Operational definition | Unit | Interpretation |
|---|---|---|---|
| Sheet angle | Tilt relative to the frontal orientation defined in the protocol | Degrees or qualitative class | Pose condition; does not describe the estimation method. |
| Capture distance | Physical separation between camera and paper plane | Millimeters or categorical class | Affects apparent scale and capture context. |
| Motion state | Sheet stationary, with small movement, or in continuous motion | Ordinal category defined in the protocol | Describes temporal condition without assuming a fixed speed. |
| Stroke displacement | Distance between reference position and observed position | Millimeters | Physical error on the sheet surface. |
| Error relative to width | Absolute error divided by sheet width | Dimensionless ratio | Normalizes scale; requires known width. |
| Angular error | Difference between reference angle and observed condition | Degrees | Characterizes orientation discrepancy. |
| Temporal drift | Change in error along the sequence | Millimeters or ratio normalized by width | Indicates accumulated change, not an internal cause. |
| Correspondence failure | Observation without a reliable reference for comparison | Count and proportion | Absence of measurement; not equivalent to null error. |

The problem is, therefore, to evaluate a relation in the sheet's frame of reference under pose variation. A page that moves may change position in the image without the stroke having moved relative to the paper. Conversely, the representation may remain almost fixed in the image and slide relative to the sheet. An evaluation that compares only image coordinates would conflate these cases. The protocol relates observations to the physical sheet and presents metrics at both scales when possible.

The distinction between stationary and moving is also necessary. A stationary capture may evaluate the geometric error of a pose, but does not reveal instability that arises during displacement. A moving sequence may accumulate synchronization and annotation uncertainty. The evaluation reports the start and end of the observed window, classifies motion in a reproducible manner, and reports cases in which the sheet ceases to be observable. No maximum speed or angle is fixed, since such limits depend on the task and need empirical justification.

Figure 1 illustrates only geometric relations among camera, sheet, angle, and distance. Figure 2 organizes crossings of angle and distance in the stationary and moving states. Figure 3 offers a curve without data to show how results could be visualized; its shape is not a quantitative prediction. These diagrams do not reveal how the system represents or computes pose.

## 4. Proposed evaluation protocol

The protocol gathers static scenes and moving sequences, with sheets of known dimensions and surfaces appropriate to the task. The question determines the variety of sheets, distances, and angles included. The sample covers combinations of orientation, distance, and motion state, preventing an angular condition from appearing only at one distance or in a single state. When a full factorial design is not practicable, the plan uses a balanced selection and declares which interactions remain uncovered.

Conditions are recorded before collection. Angle is categorized into ordered levels defined by an external procedure; distance is measured physically or grouped by apparent scale; motion is classified as stationary, small, or continuous according to a common instruction. These categories guide coverage and do not prescribe internal values. Each condition is repeated in balanced or random order when this is compatible with the experimental arrangement. Order, interruptions, lighting changes, and incidental occlusions are documented.

An independent reference records the pose and the expected stroke on the sheet. It may involve scanning the sheet at the end of the task, synchronized external annotation, or a previously defined geometric comparison procedure. The reference method must be validated against known error and its uncertainty reported. If the reference is less precise than the difference one wishes to measure, the result will be inconclusive at that scale. The team keeps reference data, observed data, and system outputs separate, without including internal details in the manuscript. Synchronization between the reference and the observation is documented with its resolution and uncertainty. When the task includes motion, the team verifies whether the records share a common time base or whether a clock difference must be estimated. The external procedure must not interfere with the gesture nor require the paper to be immobilized during all conditions. If the reference is reliable only in static scenes, the conclusion about motion will have to be limited.

Stability is measured by absolute error in millimeters and by error relative to width. The analysis describes the median, dispersion, upper quantiles, and correspondence failures per condition. The temporal trajectory of the error allows observing drift and oscillations; a start-to-end summary does not replace the per-sequence distribution. The failure rate is defined as the proportion of evaluable windows without reliable correspondence, distinguishing absence caused by occlusion from absence caused by loss of the reference. The denominator and the exclusion policy are declared.

Table 2 associates conditions and metrics. The comparison includes a generic classical geometric baseline, selected from the literature to operate as an independent reference. It receives the same data, annotations, and pose categories. The choice and the criteria are defined before comparing results, and the baseline is treated as a methodological reference, not as a gold standard. Results are presented side by side with their failures and limits.

**Table 2.** Geometric conditions and corresponding metrics, describing units, comparisons, and failures; the numerical criteria must be justified before collection and are not fixed in this proposal.

| Condition | Primary measure | Complementary metric | Comparison and interpretation |
|---|---|---|---|
| Angle by level | Absolute error in millimeters | Error relative to width | Shows physical and normalized scale. |
| Distance by level | Relative error and absolute error | Correspondence failure | Separates apparent scale from absence. |
| Stationary sheet | Error distribution per observation | Geometric bias | Characterizes stability without motion. |
| Small movement | Temporal dispersion of error | Drift along the sequence | Detects variation during limited displacement. |
| Continuous movement | Error per sequence | Failure rate and gaps | Summarizes observable continuity. |
| Classical baseline | Same measures and conditions | Paired differences | Contextualizes comparison without exposing internal details. |

![](figures/01-geometria-cena.svg)

**Figure 1.** Conceptual diagram of the camera and the sheet at distinct angular poses, with distance and motion indicated; it illustrates the physical scene and not an internal estimate or transformation method; author's own work.

![](figures/01-grade-condicoes.svg)

**Figure 2.** Proposed experimental grid crossing angle, distance, and stationary or moving state. Cells represent conditions to be observed and contain neither measurements nor results; author's own work.

![](figures/01-erro-angulo.svg)

**Figure 3.** Illustrative curve of the relation between angle and geometric error, with axes without numbers. The expected shape is not a result and does not represent measurements of the system; author's own work.

The analysis begins by verifying the quality of the reference, the coverage of conditions, and the completeness of the sequences. Then, it estimates distributions per condition and compares the measures of the evaluated system with the baseline. The difference between the two is reported with an uncertainty interval and by an appropriate sampling unit; frames from the same sequence are not treated as independent participants. If the difference depends on a condition, stratified results are presented, avoiding a global average that hides distinct behavior.

Sensitivity analysis evaluates the effect of annotation and normalization choices, provided that the alternatives are justified. If the reference definition or the missing-data policy changes, the change remains visible. The metric or condition that favors a conclusion is not selected retrospectively. The team declares how it treats extreme errors, transient failures, and stretches without a reliable reference. An exploratory analysis may suggest future hypotheses, but does not replace the previously defined analysis.

The experimental matrix must be reviewed to ensure that each category has observations in more than one combination of context. If the number of conditions makes collection impracticable, a balanced selection will be preferable to silently omitting factors. The team records the chosen combinations, the reason for exclusions, and the interactions that will not be estimated. The analysis will present coverage together with the results, so that readers can assess the distance between the planned design and the evidence obtained.

Threats include synchronization error, scanning uncertainty, lighting change, paper flexing, posture, occlusion, and limitation of the measurement unit. Calibration of the external equipment and repetition of references verify instrumental quality. The team maintains traceability of each sequence and documents deviations. The procedure does not identify the internal cause of an error; it is limited to characterizing its association with the observed conditions.

For repeated sequences, the unit of analysis must be defined in relation to the session or the sheet, not only the frame. A hierarchical analysis or a per-sequence summary may represent the dependence among observations. The statistical choice depends on the number and structure of the available data, so the protocol does not fix a model. The study describes how participants, sheets, and sessions contribute to uncertainty and publishes the sampling unit alongside each result.

The comparison with the baseline is interpreted against the same physical reference. If both approaches present similar error, the conclusion will be one of similarity observed in the sample, not of universal equivalence. If they diverge, the analysis will investigate whether the difference follows angle, distance, or motion and will report the uncertainty intervals. The baseline may also fail under certain conditions; its presence does not make a classical implementation a standard of truth.

## 5. Structure of the results

The application must report the sheets and sequences included, the coverage of angle, distance, and motion, the quality of the reference, and the conditions that could not be observed. For each condition, it will present absolute error and error relative to width, distribution, dispersion, and failure rate. The comparison with the baseline will use the same sets of observations and criteria. When the reference geometry is uncertain, the uncertainty will be reported together with the estimates, or the observation will be classified as non-evaluable according to a prior rule.

Figure 3 remains an illustrative shape and does not represent data. A future study should replace it with a visualization based on measurements, with units, conditions, and uncertainty intervals. Results by angle will not be aggregated without also showing the variation by distance and motion. The table below reserves the fields needed for the empirical phase. No error or performance value is attributed in this article.
 The filling must also record the reason for each non-evaluable sequence and the number of planned conditions that were actually observed.

**Table 3.** Planned structure for reporting absolute error, relative error, failures, and comparison with the baseline per condition; all cells await collection and remain without measured results.

| Result | Future record |
|---|---|
| Absolute error by angle and distance | [PENDING-DATA] |
| Error relative to sheet width | [PENDING-DATA] |
| Variation in stationary and moving conditions | [PENDING-DATA] |
| Correspondence failure rate | [PENDING-DATA] |
| Difference relative to the baseline | [PENDING-DATA] |
| Uncertainty of the geometric reference | [PENDING-DATA] |

## 6. Discussion

If the error remains similar across poses, the study may claim geometric stability observed under the evaluated conditions. This conclusion will be limited to the angles, distances, sheets, and movements included. The absence of a difference does not prove equivalence if the reference is imprecise or the sample too small to detect relevant variations. The sheet width and the intended use guide the interpretation of the normalized error; a fraction has no universal practical meaning.

If the error increases at certain orientations or distances, the pattern will indicate sensitivity to pose conditions. A relation between condition and error does not, by itself, identify its cause. The team should consider concomitant factors, such as contrast, focus, and motion. The illustrative curve does not predict that error grows with angle; it only shows one possible way of visualizing data once they exist. Non-monotonic results may also be informative and must be preserved.

If the absolute error increases with sheet size but the relative error remains similar, the difference may reflect physical scale. If the normalized ratio varies, the discrepancy may be related to pose or to the reference in a less straightforward way. Reporting both units helps distinguish effects of size and of physical precision, provided that the width and its uncertainty are known. A normalized measure never replaces the presentation of its source quantities.

If the classical baseline shows similar behavior, the evaluation will have evidence of comparison under shared conditions. This does not demonstrate that the methods are equivalent in other contexts nor that the baseline represents the state of the art. If the baseline diverges, the analysis must examine the same sequences and the same reference. Differences may come from a localized failure, from scale, or from temporal variability, and not from a global property.

If correspondence failures concentrate during motion, this may indicate that a static measure is not enough to characterize continuous use. The discussion will consider whether the cause is documented, but will not reconstruct internal steps of the system. If failures occur due to occlusion or absence of a reference, they will be treated as an observation limitation. The distinction avoids interpreting absence of data as extreme geometric error or perfect success.

The proposal joins principles of projective geometry, calibration, and tracking with a sheet-oriented definition. The stability criterion will depend on the task and cannot be inferred only from the shape of a curve or a global average. Its relation to document rectification is complementary: rectification aims to transform an image to facilitate reading or analysis, while this evaluation asks whether the relation of the stroke to the sheet is preserved. The literature offers conceptual tools, but the relevance of the error depends on a justified task and tolerance. The contribution is to make this dependence explicit before analyzing results.

A useful analysis will also examine cases in which the reference and the output diverge in different directions. Errors of similar magnitude may have different consequences for use depending on whether a displacement occurs along the stroke or perpendicular to it. This hypothesis must be operationalized before collection and must not be introduced after observing favorable examples. If the direction of the error does not answer the central question, the analysis will remain descriptive. The presentation of trajectories and failure examples may help interpret statistics, provided that the illustrations are chosen by a transparent rule and not only as selected extreme cases.

The unit of decision also matters. A physical error may be small when summarized over the whole page, yet affect a localized region of the stroke. Per-session distributions and examples of extreme cases complement aggregate statistics. The analysis must not hide discrepant observations merely because they increase dispersion; any exclusion requires a prior rule and a documented reason. The interpretation must also indicate whether the error relative to width was computed per observation before aggregation or from aggregated summaries, since these procedures may produce different values.

## 7. Limitations and threats to validity

Construct validity depends on whether pose represents the relevant changes. Angle, distance, and motion cover important dimensions, but do not exhaust lighting, occlusion, sheet flexing, or focus change. A pose categorized into levels may hide continuous variation. The study must explain how each level was defined, without presuming that qualitative categories are physically uniform.

Internal validity is threatened by simultaneous variation of factors. A change of angle may occur together with motion, apparent scale, and lighting. A balanced design helps, but does not eliminate all interactions. The analysis of observational data must avoid attributing causality to one condition when others also changed. The baseline compares methods under the same conditions, but does not replace randomization, a valid reference, or experimental control.

Measurement validity depends on the independent scanning or annotation. The sheet may fold, the stroke may be ambiguous, and synchronization may have error. The physical width may also be measured with uncertainty. These sources limit the interpretation in millimeters and in normalized units. The failure rate may grow when there is no reliable reference, even if the system has produced a visible response; cases without a reference must be distinguished from observable failures.

External validity is restricted to the variety of materials, sheets, equipment, distances, and activities studied. A rigid, flat sheet does not represent crumpled paper or paper resting on another surface. Results under stationary capture do not automatically generalize to motion. Participants with different strategies or motor abilities may also move the sheet in diverse ways. Conclusions must declare this scope and not use “stable” without qualifying the condition.

Data validity includes consent for images, preservation of records, and the possibility of sharing measurements. An image may contain personal content. Access restrictions must be reported and accompanied by metadata or summaries whenever permitted. This article presents no measurements, and the suitability of the protocol has not yet been examined in a pilot or by an independent team. The proposal remains subject to revision before being treated as a standard.

## 8. Conclusion

This article defined geometric stability as an observable relation between sheet pose and stroke position. It proposed measuring angle, distance, and motion, absolute error in millimeters, error relative to page width, drift, and correspondence failures. It also presented a grid of conditions and a comparison with a generic classical baseline under shared references.

The proposal does not indicate how pose is estimated nor does it present data. A future application must validate the external reference, justify error criteria, fill in the matrix of conditions, and report uncertainty. Results will need to be limited to the sheets, movements, and tasks observed. Until this evaluation, stability remains an empirical question and not a demonstrated property. The documentation of references, conditions, and uncertainties will be an essential part of this evaluation.
 The application must also justify the precision of the reference, publish the grid actually observed, and preserve divergent results across conditions. These steps make it possible to interpret the evidence without turning a conceptual diagram into a performance claim.

## Statements

- Use of generative AI: text drafted with the support of generative AI, with review and responsibility of the authors; references checked by DOI or bibliographic page.
- Data: this article presents no empirical data; future records will depend on consent and access conditions.
- Code: there is no analysis code or empirical results associated with this manuscript.
- Conflict of interest: the authors must declare pertinent conflicts before submission.
- Ethics: any collection of images involving people must obtain ethical approval and applicable consent.
- Author contributions: individual contributions must be reported in the submitted version.

## References

[1] Hartley, R.; Zisserman, A. Multiple View Geometry in Computer Vision. 2nd ed. Cambridge University Press, 2004. https://www.cambridge.org/core/books/multiple-view-geometry-in-computer-vision/0B6F289C78B2B23F596CAA76D3D43F7A
[2] Hartley, R.; Zisserman, A. Projective Geometry and Transformations of 2D. In: Multiple View Geometry in Computer Vision. Cambridge University Press, 2004, 25–64. https://doi.org/10.1017/CBO9780511811685.005
[3] Hartley, R.; Zisserman, A. Estimation – 2D Projective Transformations. In: Multiple View Geometry in Computer Vision. Cambridge University Press, 2004, 87–131. https://doi.org/10.1017/CBO9780511811685.007
[4] Hartley, R.; Zisserman, A. Algorithm Evaluation and Error Analysis. In: Multiple View Geometry in Computer Vision. Cambridge University Press, 2004, 132–150. https://doi.org/10.1017/CBO9780511811685.008
[5] Hartley, R. I. Theory and Practice of Projective Rectification. International Journal of Computer Vision, 35(2), 1999, 115–127. https://doi.org/10.1023/A:1008115206617
[6] Chum, O.; Pajdla, T.; Sturm, P. The Geometric Error for Homographies. Computer Vision and Image Understanding, 97(1), 2005, 86–102. https://doi.org/10.1016/j.cviu.2004.03.004
[7] Zhang, Z. A Flexible New Technique for Camera Calibration. IEEE Transactions on Pattern Analysis and Machine Intelligence, 22(11), 2000, 1330–1334. https://doi.org/10.1109/34.888718
[8] Tsai, R. Y. A Versatile Camera Calibration Technique for High-Accuracy 3D Machine Vision Metrology Using Off-the-Shelf TV Cameras and Lenses. IEEE Journal of Robotics and Automation, 3(4), 1987, 323–344. https://doi.org/10.1109/JRA.1987.1087109
[9] Heikkilä, J.; Silvén, O. A Four-Step Camera Calibration Procedure with Implicit Image Correction. Proceedings of the IEEE Computer Society Conference on Computer Vision and Pattern Recognition, 1997, 1106–1112. https://doi.org/10.1109/CVPR.1997.609468
[10] Poulin-Girard, A.-S.; Thibault, S.; Laurendeau, D. Influence of Camera Calibration Conditions on the Accuracy of 3D Reconstruction. Optics Express, 24(3), 2016, 2678–2686. https://doi.org/10.1364/OE.24.002678
[11] Barone, F.; Marrazzo, M.; Oton, C. J. Camera Calibration with Weighted Direct Linear Transformation and Anisotropic Uncertainties of Image Control Points. Sensors, 20(4), 2020, 1175. https://doi.org/10.3390/s20041175
[12] Cvišić, I.; Marković, I.; Petrović, I. Enhanced Calibration of Camera Setups for High-Performance Visual Odometry. Robotics and Autonomous Systems, 155, 2022, 104189. https://doi.org/10.1016/j.robot.2022.104189
[13] Liang, J.; DeMenthon, D.; Doermann, D. S. Geometric Rectification of Camera-Captured Document Images. IEEE Transactions on Pattern Analysis and Machine Intelligence, 30(4), 2008, 591–605. https://doi.org/10.1109/TPAMI.2007.70724
[14] Liang, J.; Doermann, D.; Li, H. Camera-Based Analysis of Text and Documents: A Survey. International Journal of Document Analysis and Recognition, 7, 2005, 84–104. https://doi.org/10.1007/s10032-004-0138-z
[15] Tsoi, Y.-C.; Brown, M. S. Geometric and Shading Correction for Images of Printed Materials: A Unified Approach Using Boundary. Proceedings of the IEEE Computer Society Conference on Computer Vision and Pattern Recognition, 2004, 240–246. https://doi.org/10.1109/CVPR.2004.115
[16] Brown, M. S.; Tsoi, Y.-C. Geometric and Shading Correction for Images of Printed Materials Using Boundary. IEEE Transactions on Image Processing, 15(6), 2006, 1544–1554. https://doi.org/10.1109/TIP.2006.871082
[17] Ulges, A.; Lampert, C. H.; Breuel, T. Document Capture Using Stereo Vision. Proceedings of the 2004 ACM Symposium on Document Engineering, 2004, 198–200. https://doi.org/10.1145/1030397.1030434
[18] Ma, K.; Shu, Z.; Bai, X.; Wang, J.; Samaras, D. DocUNet: Document Image Unwarping via a Stacked U-Net. Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition, 2018, 4700–4709. https://doi.org/10.1109/CVPR.2018.00494
[19] Das, S.; Ma, K.; Shu, Z.; Samaras, D.; Shilkrot, R. DewarpNet: Single-Image Document Unwarping With Stacked 3D and 2D Regression Networks. Proceedings of the IEEE/CVF International Conference on Computer Vision, 2019, 131–140. https://openaccess.thecvf.com/content_ICCV_2019/html/Das_DewarpNet_Single-Image_Document_Unwarping_With_Stacked_3D_and_2D_Regression_ICCV_2019_paper.html
[20] You, S.; Matsushita, Y.; Sinha, S.; Bou, Y.; Ikeuchi, K. Multiview Rectification of Folded Documents. IEEE Transactions on Pattern Analysis and Machine Intelligence, 40(2), 2018, 505–511. https://doi.org/10.1109/TPAMI.2017.2675980
[21] Jiang, X.; Long, R.; Xue, N.; Yang, Z.; Yao, C.; Xia, G.-S. Revisiting Document Image Dewarping by Grid Regularization. Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition, 2022, 4543–4552. https://doi.org/10.1109/CVPR52688.2022.00450
[22] Šerých, J.; Matas, J. Planar Object Tracking via Weighted Optical Flow. Proceedings of the IEEE/CVF Winter Conference on Applications of Computer Vision, 2023, 1593–1602. https://doi.org/10.1109/WACV56688.2023.00164
[23] Tsoi, Y.-C.; Brown, M. S. Multi-view document rectification using boundary. Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition, 2007. https://doi.org/10.1109/CVPR.2007.383251
[24] Lu, S.; Chen, B. M.; Ko, C. C. Perspective rectification of document images using fuzzy set and morphological operations. Image and Vision Computing, 23(6), 2005, 541–553. https://doi.org/10.1016/j.imavis.2005.01.003
[25] Lu, S.; Chen, B. M.; Ko, C. C. A partition approach for the restoration of camera images of planar and curled document. Image and Vision Computing, 24(8), 2006, 837–848. https://doi.org/10.1016/j.imavis.2006.02.008
