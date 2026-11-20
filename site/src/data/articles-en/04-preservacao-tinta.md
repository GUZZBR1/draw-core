# Temporal preservation of ink in camera-assisted drawing

## Abstract

During drawing, digital marks should preserve position, continuity, and identity as the paper and the hand move. The phrase "preserving ink" is too broad to guide evaluation without distinguishing error types. This article operationally defines three discrepancies: displaced strokes, when position diverges from a reference; fragmented strokes, when expected portions disappear; and repeated strokes, when a mark is shown more than once. It proposes measuring them by comparing observations during the activity with an independent scan of the final drawing. The protocol varies paper movement across stationary, small, and large conditions and includes erasure to examine preservation of remaining marks. Distance, coverage, gaps, and duplication metrics are treated separately to avoid an aggregate score that hides differences. Conceptual figures show the three errors, an observation sequence, and an illustrative curve without values. The system is treated as a black box. Since no data are available, the article makes no claim that any error occurs or is prevented; results remain pending until collection and comparison with the reference.

**Keywords:** ink preservation; temporal consistency; image registration; drawing; visual evaluation

## 1. Introduction

A drawing activity produces marks over time. The person adds strokes, shifts the paper, covers part of the scene with the hand, pauses, and sometimes erases sections. A digital representation may appear correct at one instant and still diverge from the drawing at the end of the session. The position of a line may change, part of a stroke may stop appearing, or a mark may appear duplicated. Without operational definitions, these situations are grouped under vague terms such as "drift", "loss", or "instability", making comparison between studies difficult.

The literature on temporal consistency in video addresses variation of appearance, alignment between frames, and preservation of objects along sequences. Research on image registration and mosaicking measures displacement and alignment between observations. Studies of digitizing whiteboards seek to preserve written content while users interact with the surface. Research on digital drawing and stroke similarity offers measures of coverage, shape, and distance; studies of digital ink also discuss continuity and perception during the gesture [25]. Each area provides useful concepts, but their outcomes are not interchangeable. A registration error between frames does not necessarily mean that a final mark is absent; a low global similarity may hide a small local duplication.

The gap motivating this article is a taxonomy applicable to ink preservation in a camera-assisted drawing system, linked to observable measures and to a temporal protocol. The proposed research question is: **how to detect and characterize displacement, fragmentation, and repetition of strokes during a session, considering movement and erasure?** The aim is to compare intermediate observations with a reference independent of the final drawing, without describing how the system accumulates, filters, or combines information.

The article offers three contributions. First, it defines three errors in operational language and associates each one with a distinct measure. Second, it organizes conditions of movement and erasure to observe their relation to temporal preservation. Third, it proposes a reference protocol, sequence-based analysis, and reporting of uncertainty, treating the system as a black box. These contributions are methodological proposals, not experimental results.

Section 2 situates the proposal in temporal consistency, image registration, and digitization of writing surfaces. Section 3 presents the taxonomy and the table of definitions, measurement methods, and units. Section 4 describes scenes, conditions, metrics, and analysis. Section 5 reserves fields for future results. Section 6 interprets possible outcomes; Section 7 delimits threats to validity; and Section 8 summarizes what is missing before empirically evaluating preservation.

The focus is drawn content that should remain visible, not aesthetic quality or automatic recognition of the drawing. This distinction avoids extending the conclusion to dimensions that will not be measured.

Preservation must be defined in relation to a reference and to a period. A comparison only between the first and last frame may not reveal when a change occurred. A comparison with the final drawing can identify accumulated differences, but does not necessarily recover the order of events. The protocol uses intermediate observations to describe when a discrepancy appears and a final scan to verify which marks remained on the physical product. This distinction between trajectory and final state guides the metrics and avoids treating the session as a single image.

The evaluation scale must also be explicit. A study may ask whether each individual mark remains intact, whether the set of the drawing keeps its form, or whether the final document remains legible. A global similarity measure serves the second question, but does not necessarily locate a fragmentation. The protocol adopts the mark as the primary unit and reports session characteristics as context. Thus, the evaluation can point out which discrepancies occurred without assuming that a small visual difference is irrelevant or that every difference implies functional harm.

## 2. Related work

### 2.1 Temporal consistency in video

Temporal consistency in video is studied in tracking, segmentation, stabilization, and frame synthesis. Methods are evaluated by object correspondence, stability of contours, alignment, and variation of appearance along sequences [1–6]. Surveys of visual tracking describe the need to measure accuracy and robustness in the face of changes of scale, illumination, occlusion, and motion. Studies of video segmentation observe that good quality on isolated frames does not guarantee coherence over time. These contributions support the use of temporal metrics, but this article does not evaluate object segmentation or video playback.

Error accumulation can be examined through trajectory, comparison of frame pairs, or contrast with an external reference. Video registration and stabilization seek to align scenes or reduce apparent motion; ink preservation, on the other hand, asks whether the stroke corresponds to the physical drawing. The physical reference changes the meaning of "stable": a page that moves in the image may remain stable relative to the paper. For this reason, temporal consistency measures must specify whether they compare image coordinates, aligned regions, or positions relative to the sheet.

Temporal metrics may include variation of displacement between observations, duration of gaps, persistence of marks, and recovery after an interruption. The choice depends on the question. A visually smooth sequence may keep a stroke displaced, while a series with small oscillations may end close to the reference. A single consistency score may hide these differences. The proposed protocol combines measures of position, coverage, and duplication and reports failures per sequence [14–21].

### 2.2 Image registration and mosaicking

Image registration estimates correspondences between observations that represent a common scene. Mosaics combine views to extend coverage or reconstruct a surface [7–10, 22–24]. This literature studies alignment error, drift, overlap, loss of correspondence, and distortions along the sequence. Studies of digitized whiteboards are particularly close because they deal with writing and drawing on a physical surface that may change position or be partially covered [11–13]. Works such as VideoToon and frame-capture systems demonstrate the usefulness of relating multiple observations to written content, although objectives and conditions vary.

The quality of a mosaic may be evaluated by point alignment, line coherence, or comparison with a reference image. A plausible visual reconstruction does not guarantee that all strokes were preserved. Duplications and fragmentations may occur locally without obviously altering the overall appearance. Studies of registration for documents and flat surfaces also address perspective distortion, curved paper, or camera motion, but their geometric metrics do not always capture the semantics of a drawn stroke.

The article uses the notion of registration only to define comparison with an external reference. It does not specify how the system obtains correspondences or maintains strokes over time. The metric compares observable positions and mark coverage, preserving the separation between internal method and experimental evidence. This scope makes it possible to discuss errors without offering a description that would reconstruct the implementation.

### 2.3 Frame digitization and stroke similarity

Whiteboard capture systems seek to transform a writing surface into a legible document and to share its content [11–13]. Digitization works investigate stroke extraction, shadow removal, geometric correction, and maintenance of writing during changes in the scene. These systems provide precedents for comparing the physical surface with a digital representation, but may operate under assumptions different from those of free drawing assisted by camera. The relevant contribution is the use of a physical reference and attention to changes over time.

Recognition of writing and drawing uses measures of similarity between sequences, curves, or images. Distance between strokes, pixel coverage, local alignment, and shape may answer distinct questions. A global image measure may penalize a change of color or thickness without indicating whether a line was displaced. A distance between curves may ignore a repeated mark outside the main correspondence. For the three errors of this article, specialized metrics are preferable: distance for displacement, gaps and coverage for fragmentation, and counting or overlap for repetition.

The final reference also has limitations. A scan may introduce shadow, deformation, or loss of thickness; a manual annotation may simplify the stroke. The literature on document quality warns that preprocessing and capture conditions affect visual measures. The protocol documents the origin and uncertainty of the reference, compares physical and digitized material in an external procedure, and avoids attributing to the system differences caused by the capture of the reference itself.

The gap is the lack of a structure that links temporal events, classes of movement, erasure, and three types of error to separate metrics. This article proposes such a structure without claiming that a published method is equivalent to the drawing context. The focus is on defining what to measure and how to report it, not on presenting an internal mechanism of preservation.

Studies of temporal consistency in stylization and tone mapping address perceptible oscillations between frames, while document registration concentrates on aligning surfaces or improving readability. Signature research, on the other hand, compares stroke sequences and distinguishes natural variation from instability. These domains provide tools and questions that differ. A classification of ink errors must preserve this difference and avoid automatically transferring a metric designed for another purpose. The proposal ties each definition to the most direct unit of evidence and anticipates analysis of ambiguities.

Future discussion may also compare participants' reports with physical measures, provided the two outcomes are presented separately. A perception of fluidity does not confirm the absence of fragmentation, and a visual difference does not necessarily imply perceived harm. This separation keeps observation and interpretation distinct.

## 3. Problem framing

The unit of analysis is a mark or group of marks identifiable on the physical drawing and in the session observations. Before comparison, the study defines which strokes belong to the reference and how to treat ambiguous, overlapping, or intentionally erased marks. The digitized final drawing constitutes the reference for the content that remained. Intermediate observations describe temporal appearance, but do not replace the physical artifact. The visual identity of a mark is assigned by annotation independent of the evaluated result, and cases without reliable correspondence are kept as non-evaluable.

**Displaced** means that a corresponding mark appears in a position different from the reference, beyond the combined uncertainty of annotation and digitization. The main measure is the distance between corresponding points or contours, expressed in millimeters on the surface or normalized by the width of the sheet. The study reports whether it reports mean distance, median, percentiles, or maximum. A mark may be displaced without being fragmented, and a constant translation must not be confused with loss of content.

**Fragmented** means that a continuous mark of the reference appears as separate segments or with missing portions in the observations. The measure may include the proportion of the reference length covered, the total length of gaps, and the number of discontinuous segments. The unit is physical length, coverage ratio, or count, depending on the procedure. The protocol determines whether a gap results from intentional erasure, transient occlusion, observation failure, or persistent absence. These causes are distinct and must not be inferred from the final image alone.

**Repeated** means that the same physical mark appears more than once in the compared representation, without corresponding to additional strokes in the reference drawing. It can be measured by the number of duplicated components, their overlap, and the distance between copies. The count depends on the rule that groups segments as the same mark. A partial duplication may look like fragmentation under another definition; for this reason, the annotation manual describes examples and ambiguous cases before analysis. The classification may admit more than one type of error when this represents the observation more faithfully.

The cost of each discrepancy depends on the use. A small displacement may be acceptable for an expressive annotation, but a fragmented stroke may change the interpretation of a word or diagram. A repeated copy may make a drawing visually cluttered even when the original mark remains. The protocol does not convert these differences into fixed weights. If the study produces a composite score, each weighting must come from a declared purpose and be presented alongside the separate measures. The qualitative classification of errors must precede any synthesis, to keep the relation between observation and interpretation.

Table 1 summarizes definitions, comparison, and unit. Metrics are calculated relative to the digitized final reference and to the corresponding intermediate observations. The reference is recorded externally, without exposing how ink is represented inside the system. The unit of error must be compatible with the question: physical displacement, stroke coverage, or number of duplications. A count without a denominator, or a ratio without a definition of length, does not allow comparison.

**Table 1.** Operational definitions of displacement, fragmentation, and repetition of ink, with reference comparison and unit of measure; the criteria apply to the observable representation over time.

| Error | Definition | How to measure against the reference | Possible unit |
|---|---|---|---|
| Displaced | Corresponding mark in a position different from the physical drawing | Distance between paired strokes or contours | Millimeters or ratio to sheet width |
| Fragmented | Expected continuous stretch appears separated or absent | Coverage of the reference and length of gaps | Ratio, millimeters, or count of segments |
| Repeated | One physical mark corresponds to multiple copies in the representation | Count of duplications and overlap between copies | Count or proportion of affected marks |

These definitions do not impose a causal order. A mark may shift and then fragment, but the protocol classifies observations according to the available evidence, without deducing what occurred inside the system. The report may describe the sequence of observed events, such as "displacement followed by absence", if the frames support that description. It must not infer internal operations from the final appearance.

Movement is categorized by observable condition: stationary sheet, small movement, or large movement. The operational description uses the physical trajectory recorded externally and levels defined before analysis. There is no universal value that separates small from large; the study justifies the categorization and keeps continuous units available when instrumentation allows. Erasure is a separate condition: part of the drawing is intentionally removed while other marks must remain. The evaluation observes whether preserved marks remain aligned, complete, and without duplication.

Figure 1 illustrates the errors visually. Figure 2 shows an external sequence of observations and a final comparison. Figure 3 presents only one possible curve shape to explore drift according to movement; without data, it suggests neither direction nor magnitude. These figures are conceptual and do not describe the internal chain of the system.

## 4. Proposed evaluation protocol

The study gathers reference drawings and observation sequences during defined tasks. The drawings are digitized at the end under described conditions and with resolution appropriate to the question. The team records the dimensions of the sheet, orientation, capture distance, and movement states. The task includes periods of continuous stroke, pause, resumption, and erasure of selected marks, if these actions are relevant to the objective. The order of conditions is balanced or randomized when this does not impair the task.

The collection must cover different types of mark, such as long lines, short segments, curves, and crossings, without assuming that their geometry determines performance. The protocol records whether strokes overlap or lie close together, since such cases hinder correspondence. A sample is annotated by independent evaluators who receive common instructions. The team computes disagreement and resolves ambiguities by a previously defined procedure. Marks that cannot be identified with confidence are excluded from the main measure, but their frequency is reported.

Movement conditions include stationary sheet, small movement, and large movement. The classification is supported by external recording of the sheet, without relying on internal measures. For each level, observations are synchronized with the digitized final drawing. The erasure condition removes a selected part of the drawing and records which marks should remain. The protocol specifies whether erasure occurs before or during the session, since timing changes the valid reference. A separate analysis may consider pause, return, and hand occlusion, but must not mix them with the erasure effect.

Metrics are computed per mark, per sequence, and per condition. Displacement uses the physical distance between corresponding strokes, normalized by width if dimensions vary. Fragmentation uses coverage of the reference length, extent of gaps, and number of separated segments. Repetition uses the number of duplications and the fraction of affected marks. The team also computes a rate of correspondence failure and reports whether its origin is known or unknown. These metrics remain separate; a composite score could hide that one type of error improves while another worsens.

The team records the reference length before estimating coverage and documents how it separates nearby marks. For distance, the procedure defines which segments are compared and how crossings are treated. For repetition, annotators check whether similar components correspond to an original mark or to an additional stroke made by the person. These decisions are assessed on an independent sample and reported by category. If agreement is low, the ambiguous cases are presented separately instead of forcing a single classification. Training material is not included in the evaluation sample, so that criteria are not tuned to selected examples.

Temporal analysis describes when each discrepancy appears and whether it persists until the end. A frame-by-frame comparison must not assume independence between consecutive observations. The resampling unit follows the session, sheet, or participant, depending on the design. Results are summarized with distribution, uncertainty intervals, and examples selected by a documented rule. The study does not attribute a cause to a specific movement if illumination, occlusion, or framing also change.

Figure 1 presents the three errors in visual language; Figure 2 organizes start, intermediate observation, and final scan; Figure 3 shows an illustrative form without values. The sequence is built from external records and the physical reference. The figures do not describe how marks are combined or maintained internally.

![](figures/04-tres-erros.svg)

**Figure 1.** Diagram of the three ink preservation errors: displaced stroke, fragmented stroke, and repeated stroke. These are conceptual diagrams compared with an independent reference and do not show internal processes; author's own work.

![](figures/04-sequencia-quadros.svg)

**Figure 2.** Conceptual sequence among start, intermediate observation, and final scan, used to contextualize temporal comparisons. The frames do not represent measurements or an internal sequence; author's own work.

![](figures/04-deriva-movimento.svg)

**Figure 3.** Illustrative curve of stroke drift according to movement condition, with axes without numbers. The expected form is not a result; it does not anticipate measured behavior; author's own work.

Table 2 synthesizes conditions and metrics. The study defines qualitative levels before collection and describes how small and large movement were distinguished. The erasure condition evaluates preserved and removed marks separately, making it possible to verify whether intentionally erased content is confused with a preservation error. It is not assumed that every stroke must remain after erasure; the reference and the goal of the task determine what must be compared.

**Table 2.** Movement and erasure conditions to compare, linked to drift and preservation metrics; levels are defined by the study and do not represent observed results.

| Condition | Observed evidence | Main metric | Interpretation |
|---|---|---|---|
| Stationary sheet | Sequence without deliberate displacement | Distance and fragmentation | Reference for a temporally stable condition. |
| Small movement | Limited displacement defined in the protocol | Drift and coverage | Variation under lower-amplitude movement. |
| Large movement | Broader displacement defined in the protocol | Drift, failure, and repetition | Condition of greater geometric demand. |
| Erasure | Intentional removal of selected marks | Preservation of remaining strokes | Distinguishes intended change from unintended loss. |

The analysis line begins by verifying the quality of digitization, synchronization, and annotation agreement. It then classifies marks by error type and computes measures per condition. The team compares patterns between movement and rest, and examines whether erasure affects marks that should remain. Uncertainty intervals respect the dependence within each session. Extreme values are kept unless an instrumental failure, defined in advance, justifies exclusion.

The concern that a final scan may alter thickness or contrast is handled by an independent procedure and by recording the uncertainty. Distance-based comparisons must not attribute precision beyond the resolution of the reference. If the physical mark is ambiguous, the uncertainty annotation remains visible. The protocol also documents capture failures, missing frames, and occlusions to separate instrument limitations from persistent observed discrepancy.

The annotation manual includes simulated cases or training examples that do not enter the main analysis. These examples clarify when a mark is considered interrupted and when a gap is merely an intentional part of the drawing. Annotators receive no information about the movement condition whenever this is not needed to recognize the stroke. Agreement between annotators is presented by error category, since differences may be larger for repetition than for displacement. Adjudication records which evidence was used and does not alter the definition after the results have been observed.

## 5. Structure of the results

The application will present the composition of the drawings, the types of strokes evaluated, and the coverage of movement and erasure conditions. For each sequence, the report will state which marks could be paired with the reference, which remained ambiguous, and which were excluded according to the plan. The results for displacement, fragmentation, and repetition will be shown separately, with units, distribution, and uncertainty. The analysis will indicate when a failure resulted from occlusion, reference failure, intentional erasure, or observable discrepancy without known cause.

The temporal analysis will describe whether a discrepancy appeared in an intermediate observation and remained until the final comparison. A final measure will not replace the record of when the change occurred. Figure 3 will remain only an illustrative form until measured data exist. A future figure should show units and conditions and not reuse the schematic curve as if it were an observation. Table 3 reserves the fields to be filled in. In this manuscript, all of them remain [PENDING-DATA].
 The application will also indicate the version of the annotation manual, the synchronization procedure, and the way physical units are calculated.
 The analysis should also report excluded sequences and the reason for each exclusion.

**Table 3.** Structure of future results for displacement, fragmentation, and repetition, organized by condition and reference; no cell contains measurements because the protocol has not yet been applied.

| Result | Future record |
|---|---|
| Displacement by movement state | [PENDING-DATA] |
| Coverage and gaps of strokes | [PENDING-DATA] |
| Repeated marks per sequence | [PENDING-DATA] |
| Observed effect after erasure | [PENDING-DATA] |
| Annotation disagreement and reference failures | [PENDING-DATA] |

## 6. Discussion

If the distance between strokes remains small and stable in the observed conditions, the study may claim spatial preservation for the sample and reference used. This conclusion does not imply absence of fragmentation or repetition. Each error requires its own analysis. A low mean may coexist with a few important failures, which is a reason to present the distribution and examples selected by a transparent rule. The purpose of use determines whether a given variation is acceptable; this proposal does not contain a universal margin.

If fragmentation increases during movement, the pattern will indicate an association between that condition and observed gaps. The study should verify whether the gaps appear in stretches of low visibility, occlusion, or loss of external recording. Without sufficient evidence, the association does not identify a cause. If marks are intentionally erased, the comparison must exclude the removed marks from the fragmentation category and concentrate on the content that should remain. An incorrect reference policy could classify intended erasure as an error.

If repeated marks appear, they may represent duplication, annotation ambiguity, or a change in the drawing itself. Reviewing examples and agreement between annotators helps distinguish these cases, but does not make the interpretation automatic. Localized repetition may be relevant even when a global similarity measure is high. Disaggregated presentation preserves information about the location and identity of the mark.

If displacement is constant throughout the session, the final mean may hide a persistent bias. If displacement varies and then returns, a comparison between start and end may suggest a stability that did not exist during the activity. Intermediate observations are necessary to represent the trajectory. Conversely, very sparse sampling may miss brief oscillations. The protocol must explain how its cadence was chosen and limit inferences to changes it can observe.

If erasure affects unselected marks, the result may point to an interaction between the act of erasing and the preservation of the rest of the drawing. This interpretation requires a clear description of which marks should remain present and how the reference was established. If only the final scan is available, it will not be possible to state at what moment the content was lost. A complete temporal comparison separates the final result from the observed trajectory.

The proposal engages with research on video consistency, document mosaics, whiteboard capture, and stroke similarity [1–21]. These areas offer analogous metrics and problems, but do not necessarily share unit or purpose. Global image alignment does not directly measure the semantic fragmentation of a mark; signature similarity is not automatically valid for free drawing. The value of the protocol lies in making explicit definitions and units that can be tested in their own context.

A result with no observed discrepancies will still depend on the sensitivity of the instrument and on the coverage of movements. The absence of errors may reflect a scene set that is not demanding or a metric that does not capture brief events. For this reason, future discussion will combine frequency of discrepancies, amplitude, duration, and context, and will present detection limits. An aggregate rate without a description of exposure will not allow the conclusion that ink remained preserved throughout the session.

If the three categories vary in different directions, the study should resist summarizing the set in a global classification. Displacement may decrease while fragmentation increases, or an erasure condition may alter repetition without altering position. These mixed patterns can guide a subsequent hypothesis about the task and the instruments. Interpretation must remain at the level of observed association, without explaining the change by an unmeasured internal process.

The comparison with digital signature literature is particularly limited by the structure of the marks. Signatures tend to have temporal order and an authentication purpose, while free drawings may combine independent and overlapping lines. Signature similarity metrics are useful to inspire sequential comparisons, but do not validate a measure of fragmentation for drawing. The proposal requires a pilot in the domain of interest and does not treat transfer between tasks as guaranteed.

## 7. Limitations and threats to validity

Construct validity depends on whether the taxonomy represents the relevant discrepancies. Displacement, fragmentation, and repetition do not cover every possible error. A change in thickness, color, shape, or order of marks may affect the experience without clearly fitting one of the categories. A study may record these additional dimensions, but should keep them separate rather than forcing an inadequate classification. The choice of the mark as unit may also be difficult in drawings with overlapping strokes or without clear visual segmentation.

Internal validity is threatened by simultaneous changes in movement, occlusion, illumination, and erasure. An observed difference after an action does not demonstrate that the action caused it if other conditions changed. The protocol recommends balancing and recording, but does not eliminate confounding. Task order, familiarity with the activity, and drawing strategy may influence the session. The analysis must preserve temporal dependence and must not treat consecutive frames as independent replications.

Measurement validity depends on digitization, alignment, annotation, and synchronization. The final drawing may be deformed by the paper, stroke thickness may vary, and the reference may lose small marks. Length measures depend on physical scale; overlap depends on geometric registration; counting depends on the definition of identity. Reference uncertainty must accompany each metric. A digitization without sufficient quality may render the conclusion inconclusive.

External validity is limited by the variety of paper, drawing tool, tasks, environments, and participants. An activity with long lines may not represent letters, diagrams, or shading. Small and large movement are categories dependent on the study, not universal classes. The result must be limited to the conditions observed and not generalized to every form of drawing or use.

Data validity includes image privacy, consent, licensing, and availability of the sequences. Drawn content may reveal personal or authorial information. Access restrictions reduce independent auditing but may be necessary. The study must explain which materials can be shared and offer descriptions or summaries compatible with the restrictions. This manuscript does not present data nor validate the taxonomy in a pilot application.

## 8. Conclusion

This article defined three observable errors of ink preservation: displacement, fragmentation, and repetition. It proposed comparing them with an independent scan of the final drawing and observing their evolution during a session. The protocol varies paper movement across stationary, small, and large conditions and includes erasure to distinguish intentional removal from loss of marks that should remain.

The proposal does not describe internal mechanisms and does not claim that these errors occur in any system. A future application will need to validate the reference, instruct annotators, record uncertainty, and fill the pending fields with measured sequences. Conclusions will have to remain limited to the marks, tasks, and conditions included. Until such an application exists, the taxonomy and metrics are proposals for evaluation, not evidence of preservation.
 The protocol should be revised after a pilot if the categories cannot be applied consistently, keeping a record of changes and their justification.
 The choice of metrics and units will be published together with the description of the conditions to allow independent comparison.

## Statements

- Use of generative AI: text drafted with the support of generative AI, with review and responsibility of the authors; references checked by DOI or bibliographic page.
- Data: this article does not present empirical data; future images will depend on consent, license, and appropriate protection.
- Code: there is no analysis code for results associated with this manuscript.
- Conflict of interest: the authors must declare relevant conflicts before submission.
- Ethics: studies with participants must obtain ethical approval and consent before collection.
- Author contributions: individual contributions must be reported in the submitted version.

## References

[1] Bonneel, N.; Tompkin, J.; Sunkavalli, K. et al. Blind Video Temporal Consistency. ACM Transactions on Graphics, 34(6), 2015, Article 196. https://doi.org/10.1145/2816795.2818107
[2] Aydın, T. O.; Stefanoski, N.; Croci, S.; Gross, M.; Smolic, A. Temporally Coherent Local Tone Mapping of HDR Video. ACM Transactions on Graphics, 33(6), 2014, Article 196. https://doi.org/10.1145/2661229.2661268
[3] Chen, T.; Cheng, M.-M.; Tan, P.; Shamir, A.; Hu, S.-M. Automatic Motion-Guided Video Stylization and Personalization. Proceedings of ACM Multimedia, 2011, 1041–1044. https://doi.org/10.1145/2072298.2071933
[4] Shekhar, S.; Reimann, M.; Hilscher, M. et al. Interactive Control over Temporal Consistency while Stylizing Video Streams. Computer Graphics Forum, 42(4), 2023, e14891. https://doi.org/10.1111/cgf.14891
[5] Ozcinar, C.; Lauga, P.; Valenzise, G.; Dufaux, F. Spatio-temporal constrained tone mapping operator for HDR video compression. Journal of Visual Communication and Image Representation, 54, 2018, 166–178. https://doi.org/10.1016/j.jvcir.2018.06.003
[6] Lu, C.; Xiao, Y.; Tang, C.-K. Real-Time Video Stylization Using Object Flows. IEEE Transactions on Visualization and Computer Graphics, 24(6), 2018, 2051–2063. https://doi.org/10.1109/TVCG.2017.2700470
[7] Zitová, B.; Flusser, J. Image registration methods: a survey. Image and Vision Computing, 21(11), 2003, 977–1000. https://doi.org/10.1016/S0262-8856(03)00137-9
[8] Ghosh, D.; Kaabouch, N. A survey on image mosaicing techniques. Journal of Visual Communication and Image Representation, 34, 2016, 1–11. https://doi.org/10.1016/j.jvcir.2015.10.014
[9] Kumar, G. H.; Shivakumara, P.; Guru, D. S.; Nagabhushan, P. Document image mosaicing: A novel approach. Sādhanā, 29(3), 2004, 329–341. https://citeseerx.ist.psu.edu/document?doi=394002f63fedafe63691ec8fa072af9d2b942a0d&repid=rep1&type=pdf
[10] Srinath, S.; Ravikumar, C. N. Braille Document Image Mosaicing: A Novel Approach. International Journal of Computer Applications, 103(6), 2014, 32–36. https://doi.org/10.5120/18081-8906
[11] Zhang, Z.; He, L.-W. Whiteboard scanning and image enhancement. Digital Signal Processing, 17(2), 2007, 414–432. https://doi.org/10.1016/j.dsp.2006.05.006
[12] Arango Duque, C. A.; Abebe, M. A.; Shahid, M.; Hardeberg, J. Y. Color and Quality Enhancement of Videoconferencing Whiteboards. Journal of Perceptual Imaging, 1(1), 2018, 010504-1–010504-13. https://doi.org/10.2352/J.Percept.Imaging.2018.1.1.010504
[13] Courtney, J. CleanPage: Fast and Clean Document and Whiteboard Capture. Journal of Imaging, 6(10), 2020, 102. https://doi.org/10.3390/jimaging6100102
[14] Iwata, K.; Kise, K.; Nakai, T. et al. Capturing Digital Ink as Retrieving Fragments of Document Images. 10th International Conference on Document Analysis and Recognition, 2009, 1236–1240. https://doi.org/10.1109/ICDAR.2009.192
[15] Huang, K.; Yan, H. Stability and style-variation modeling for on-line signature verification. Pattern Recognition, 36(10), 2003, 2253–2270. https://doi.org/10.1016/S0031-3203(03)00126-2
[16] Rashidi, S.; Fallah, A.; Towhidkhah, F. Similarity evaluation of online signatures based on modified dynamic time warping. Applied Artificial Intelligence, 27(7), 2013, 599–617. https://doi.org/10.1080/08839514.2013.813187
[17] Manabe, Y.; Chakraborty, B. Efficient On-line Handwritten Signature Verification by Integrating DTW and Proposed Local Dynamic Similarity Measure. Journal of Japan Society for Fuzzy Theory and Intelligent Informatics, 24(6), 2012, 1165–1176. https://doi.org/10.3156/jsoft.24.1165
[18] Huang, K.; Yan, H. On-line signature verification based on stroke matching. Proceedings of the International Conference on Document Analysis and Recognition, 2002. https://staff.itee.uq.edu.au/lovell/aprs/dicta2002_proceedings/Huang219.pdf
[19] Fischer, A.; Plamondon, R. Signature verification based on the kinematic theory of rapid human movements. IEEE Transactions on Human-Machine Systems, 47(2), 2017, 169–180. https://doi.org/10.1109/THMS.2016.2634922
[20] Doroz, R.; Kudłacik, P.; Porwik, P. Online signature verification modeled by stability oriented reference signatures. Information Sciences, 460–461, 2018, 151–171. https://doi.org/10.1016/j.ins.2018.05.049
[21] Swaileh, W.; Imbert, F.; Soullard, Y. et al. Online handwriting trajectory reconstruction from kinematic sensors using temporal convolutional network. International Journal on Document Analysis and Recognition, 26, 2023, 289–302. https://doi.org/10.1007/s10032-023-00430-1
[22] Liang, J.; DeMenthon, D.; Doermann, D. S. Geometric Rectification of Camera-Captured Document Images. IEEE Transactions on Pattern Analysis and Machine Intelligence, 30(4), 2008, 591–605. https://doi.org/10.1109/TPAMI.2007.70724
[23] Tsoi, Y.-C.; Brown, M. S. Multi-view document rectification using boundary. Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition, 2007. https://doi.org/10.1109/CVPR.2007.383251
[24] Puybareau, É.; Géraud, T. Real-Time Document Detection in Smartphone Videos. Proceedings of the IEEE International Conference on Image Processing, 2018, 1498–1502. https://doi.org/10.1109/ICIP.2018.8451533
[25] Annett, M. (Digitally) Inking in the 21st Century. IEEE Computer Graphics and Applications, 37(1), 2017, 92–99. https://doi.org/10.1109/MCG.2017.1
