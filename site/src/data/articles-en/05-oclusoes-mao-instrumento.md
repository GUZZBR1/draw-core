# Hand and instrument occlusions in camera-assisted drawing

## Abstract

The hand and writing instrument cover the page during drawing; this occlusion is a normal part of the activity, not an artificial exception to remove from testing. Evaluating its effects requires specifying duration, motion, and covered region, as well as measuring how much of the page is occluded. This article proposes a taxonomy and protocol for studying a camera-assisted drawing system under these conditions. The classification separates brief, intermediate, and long episodes; low, moderate, and broad movement; and occlusion at the edge, center, or combined regions. The occluded fraction is defined as covered area relative to page area, with no fixed acceptance value. The protocol relates each condition to detection, continuity, and recovery time after the hand leaves. Conceptual figures illustrate postures, a condition matrix, and a curve without data. Since no results are available, the article does not claim that occlusion causes failures or describe how the system handles it; these relationships remain for empirical evaluation.

**Keywords:** occlusion; pen interaction; hand; continuity; usability evaluation

## 1. Introduction

The hand and the writing instrument cover part of the page during drawing. This occlusion is a normal part of the activity and should be treated as a condition of use, not as an artificial exception to be eliminated from the evaluation. The person positions the hand to support the gesture, reaches different regions of the paper, and moves the instrument over the freshly produced mark. Occlusion may be brief or persistent, may cover the edge or the center, and may accompany small or broad movement. These cases impose distinct demands on continuity and recovery.

An evaluation that simply reports "there is occlusion" does not explain how much area was hidden, for how long, or with what movement. Nor does it distinguish whether the observable output maintained continuity during the coverage, was absent, or returned after the hand left. Without this separation, studies may conflate experimental condition and interpretation. The effect of occlusion needs to be measured without describing how a camera-assisted drawing system detects or handles the hand.

The computer vision literature studies occlusion in object tracking, gesture recognition, and hand segmentation. Research on pen interaction discusses posture, contact, resting regions, and conflicts between hand and surface. Digital tabletop or interactive paper systems also investigate how people write while the body occupies part of the field of view. These works ground factors and forms of evaluation, but their results do not transfer automatically to a different drawing task or to a specific system. Studies of direct pen interaction show that hand position, unintended contact, and posture vary with the surface and the task [1, 4, 10, 11].

The gap addressed by this article is a structure for classifying hand and instrument occlusions by duration, movement, and covered region, relating each level to measures of detection, continuity, and recovery. The proposed question is: **how are the duration, movement, and location of occlusion associated with observable availability and continuity during drawing?** The proposal also measures the fraction of the page covered, so that results can be related to quantity and not only to a qualitative category.

The article offers three contributions. First, it defines a three-axis taxonomy with operational levels that can be described before data collection. Second, it specifies the occluded fraction and metrics of continuity, detection, and recovery. Third, it proposes a protocol that compares occlusion episodes with periods without coverage, keeping the system as a black box. None of these contributions constitutes an experimental result or claims that a given level is tolerable. The protocol also specifies which methodological decisions must be declared so that a comparison between sessions does not confuse the covered geometry with differences in instructions, instrument, or framing.

Section 2 reviews occlusion in tracking, hand segmentation, pen interaction, and digital paper systems. Section 3 defines the axes and presents the classification table. Section 4 connects the conditions to the measures and describes collection, analysis, and threats. Section 5 reserves fields for later results. Section 6 interprets possible patterns; Section 7 delimits threats to validity; and Section 8 summarizes the evidence still needed.

The occluded fraction is important because categories such as "partial" may cover very different quantities. It is defined as the area of the covered region divided by the total area of the page, observed at a declared time point. The fraction may vary within the same episode, so a single observation does not necessarily summarize the whole duration. The protocol keeps this continuous measure alongside the qualitative levels and does not choose a fixed value as a success criterion.

Occlusion is also distributed differently depending on posture and task. A person may rest the hand on the edge while drawing in the center, or cover the work area with the palm and instrument. Handedness, sitting position, and page size may influence these postures. A protocol that forces a single posture may not represent everyday use. Therefore, data collection should include natural action and record how the experimental instructions influence behavior, without interpreting differences in posture as a general capability of the participant.

## 2. Related work

### 2.1 Occlusion in visual tracking and detection

Occlusion is a recurrent source of difficulty in object tracking. Tracking surveys distinguish partial and complete occlusion, reappearance, confusion between objects, and loss of identity. Methods are evaluated by localization accuracy, failure duration, and ability to recover the target. In a drawing task, the object of interest is the page and the relevant output is its availability for interaction; the hand may cover a part without hiding the whole page. Therefore, object benchmark metrics need to be adapted to the geometry and purpose of drawing.

Hand segmentation and gesture recognition study how the hand appears against varied backgrounds and how movement alters shape and appearance. Classical works use color, shape, contour, or supervised learning, while modern reviews discuss datasets and challenges of illumination, posture, and occlusion. This article does not compare segmentation methods or describe how a system processes hands. The literature is used to motivate the description of posture, covered region, and temporal variation.

Occlusions may also be intentional. A hand that covers the work area may hide part of the drawing for a duration associated with natural movement. Unlike an external obstruction, its location may follow the stroke and move across the paper. Measuring the occluded fraction in each interval makes it possible to describe this variation without inferring an internal mechanism. The comparison between unoccluded and occluded episodes should keep the other conditions similar when the goal is to isolate association.

### 2.2 Hand segmentation and pen interaction

Pen and paper interaction includes contact, posture, hand support, reach, and coordination between instrument and surface. Studies of pen interfaces identify conflicts between the intention to draw, palm support, and content manipulation. Work on palm rejection or bimanual interaction demonstrates that the hand can be simultaneously part of the action and a source of occlusion. This duality grounds an evaluation that does not treat the presence of the hand as abnormal noise. Instead of considering the hand merely as an obstacle, studies explore occlusion-aware interfaces and show that the location of content relative to the hand matters for interaction [2, 3, 5, 6, 7, 8].

Optical pen tracking systems investigate accuracy, alignment, and movement of the instrument on ordinary surfaces. Although these systems have varied goals, they provide precedents for measuring interaction through external records and for distinguishing instrument movement from drawn content. The protocol in this article does not reveal how the hand or instrument is detected or handled. It observes input conditions and visible responses, with independent annotation of the covered region.

The hand segmentation literature also warns that appearance and shape vary with illumination, skin tone, gloves, distance, and background. These dimensions may interact with the covered fraction. Therefore, the sample should describe relevant characteristics of the context without inferring performance for all people. When demographic data are collected, their purpose, consent, and protection must be made explicit. The evaluation should avoid universal generalizations from few participants or configurations.

### 2.3 Digital tabletops and paper interaction

Digital tabletops and surface interfaces allow writing, drawing, and direct manipulation. Research on multi-user interaction, digital paper, and whiteboard capture observes how hands and instruments cover content during tasks. These studies distinguish interaction by touch, pen, physical object, and movement over the surface. The user's natural posture may reduce the visibility of marks, but also indicates where the activity is taking place. This interaction between signal and context is relevant for interpreting continuity.

Vision studies on tables or interactive surfaces sometimes measure recovery latency, loss of contact, or localization accuracy. The metric "time to recover" needs to define when the occlusion ended and when a response is considered available again. If the hand leaves gradually, the end may be ambiguous; the protocol must identify the observable landmark and the uncertainty. Recovery may also depend on task interruption or residual movement, which should be recorded.

The literature offers several components, but not a common taxonomy that crosses duration, movement, and covered region with occluded fraction and recovery in camera-assisted drawing. Some lines prioritize instantaneous detection; others favor pen interaction; still others study shared surfaces. The gap addressed by this article is to integrate these dimensions in a black-box evaluation, without assuming that a specific posture is defective or that a given internal treatment exists. Research on digital paper, shadow tracking, physical objects, and gestures near the surface broadens the repertoire of observable situations [13–17, 22–24]. Even so, the unit of evaluation here is the episode of page coverage during drawing, not the classification of a gesture nor the performance of a specific device.

The natural interaction literature also shows that occlusion can be functional. The hand provides support, coordination, and visual reference for the gesture, although it temporarily hides the surface. The evaluation should avoid labeling all coverage as error and instead ask what observable information is necessary for the activity to continue. Interactive surface systems may use different sensors and representations, so their results serve as context and not as direct comparison. The current protocol keeps its focus on the visible output during use with paper and describes the condition without assuming a common implementation across studies.

Recovery time is an especially pertinent measure after persistent occlusion. Tracking studies generally report success in locating a target, but the moment at which the observation becomes useful again may depend on the task. Recovery does not mean merely that the page returned to the field of view; it requires the external response defined by the protocol. The literature provides motivation for separating recovery from instantaneous accuracy, but does not determine an acceptable interval for drawing. This interval needs to be investigated according to the activity and users' expectations.

There are also works on pen input complemented by mid-air gestures, tip tracking, and collaborative drawing that help delimit the scenario. They show that graphic activities can combine contact, movement above the surface, and coordination between people, although these contexts are not equivalent to involuntary coverage of the page [19–21, 25]. The resulting synthesis separates three levels of evidence: physical observation of the hand, visible response of the interaction, and interpretation of the quality of the activity. This separation avoids attributing to occlusion an effect that could stem from a pause, a change of task, or displacement of the sheet.

The protocol also benefits from distinguishing the study of visual recognition from the experience of drawing. An artificial task asking the person to cover a region may increase repeatability but alter posture and rhythm. A free task approximates spontaneous use but may generate fewer occurrences of a rare condition. The literature does not resolve this trade-off for all surfaces and groups. The proposed design records whether the coverage was spontaneous or instructed and reports the two types separately, preserving context for interpreting the occurrence and the response.

## 3. Problem framing

The primary unit is an occlusion episode, defined as an interval in which the hand or instrument covers an annotatable part of the page. The start occurs when the covered region exceeds the previously established visual criterion; the end occurs when it becomes visible again according to the same rule. If the coverage oscillates, the study defines whether adjacent episodes are merged or kept separate. The rule is applied from the external record and does not depend on observing the system's response.

The classification uses three independent axes. **Duration** may be brief, intermediate, or long, with temporal boundaries chosen and justified by the protocol. **Movement** may be small, moderate, or broad, measured by the external trajectory of the hand or instrument during the episode. **Region** may correspond to the edge, the center, or multiple areas. The level of each axis is annotated separately; a long occlusion does not necessarily imply broad movement, and a central occlusion may be brief.

Occluded fraction is the proportion of the page area covered at an instant or aggregated over a declared interval. If Aₒ represents the covered area and Aₚ the total area of the page, the fraction is f = Aₒ/Aₚ. The measure depends on the geometric reference of the page and on the annotation of the hand. It can be computed on sampled observations and summarized by distribution over the episode. The proposal does not prescribe a numerical acceptance limit, since any value depends on the task and will have to be studied.

The observable effect can be described along three dimensions. **Detection availability** indicates whether the page continues to be reported as present according to the study's external criterion. **Continuity** records whether the stroke maintains visual relation throughout the episode and upon reappearance of the area. **Recovery** measures the time between the observable end of the occlusion and the return of the response that meets the availability criterion. These measures characterize output and time, but do not report how the hand is handled internally.

Table 1 organizes the axes and levels. To reduce ambiguity, the manual presents schematic examples and rules for partially overlapping occlusions, gradual change of coverage, and an instrument crossing the page with no visible hand. Difficult cases are marked as uncertain instead of receiving a forced classification. An episode may include more than one region or vary in position during its duration; the annotation preserves this change when sampling allows.

**Table 1.** Classification of occlusion by duration, movement, and covered region, with qualitative levels and operational descriptions; the axes are recorded separately to avoid confusing different causes.

| Axis | Qualitative levels | Operational definition | Complementary record |
|---|---|---|---|
| Duration | Brief; intermediate; long | Interval between observable start and end | Continuous time of the episode |
| Movement | Small; moderate; broad | External displacement during coverage | Trajectory or category defined beforehand |
| Region | Edge; center; combined | Location of the covered area on the page | Occluded fraction per observation |

The relationship between occlusion and performance is not necessarily monotonic. Covering a small region may be critical if it coincides with an important area, whereas greater coverage in another region may not interrupt the task. The occluded fraction measures quantity, not semantic importance. The protocol should record, when relevant, the position of the active stroke and distinguish the region in which the person works from the covered region. This information makes it possible to interpret continuity without claiming that every area has the same weight.

The framing also distinguishes occlusion, erasure, and absence of the page. Occlusion is transient coverage by the hand or instrument; erasure intentionally alters the content; absence indicates that the page is not present or cannot be observed by the protocol. These events require distinct metrics. The protocol does not use coverage as the presumed cause of any failure: it compares the observed occurrence with reference conditions and reports associations.

The taxonomy also records whether the instrument covers a freshly produced mark or another region. This distinction may help interpret continuity, but does not alter the definition of occluded fraction. The person may move the hand without the total covered area changing much, or change the coverage while remaining almost still. Thus, movement and fraction are related but not redundant measures. The classification is assigned per episode and the analysis presents its temporal variability when the resolution of the record allows.

Figure 1 illustrates postures in which distinct regions are covered. Figure 2 crosses duration and region, keeping movement as an additional axis. Figure 3 presents only an illustrative shape of performance as a function of the covered fraction. None of the figures contains data or describes the internal handling of the hand or instrument.

## 4. Proposed evaluation protocol

Data collection comprises sessions in which people draw with the hand and writing instrument visible in an external recording. The protocol describes task, sheet, capture position, lighting, and instructions. The activities include moments of continuous stroke, pauses, hand displacement, and coverage of distinct regions. The team does not request artificial postures that prevent natural action, but may use instructions to ensure coverage of necessary categories. Participants consent to the recording, and images are protected according to the ethics plan.
 A pilot verifies whether the planned episodes occur without unusual effort and whether annotators can identify start, end, and covered region. If certain postures do not occur spontaneously, they may be induced only when this corresponds to the question and is ethically acceptable. The study distinguishes natural from instructed conditions.

Sampling crosses duration and region with movement. A fully factorial design may generate many conditions, so a balanced selection maintains coverage per axis and prioritizes justified interactions. Task order is alternated or randomized when practicable. The team records handedness, general type of instrument, and pertinent experience only when this answers the question; collecting personal characteristics requires justification and consent. The study should not generalize to all users on the basis of a restricted sample.

Annotation is conducted by people who do not see the performance metric of the condition, when possible. Instructions define episode start and end, region, movement, and covered fraction. A sample is annotated independently to assess agreement. Rapid overlaps, a thin instrument, and shadow may make boundaries uncertain; the manual records uncertainty and an adjudication procedure. The fraction is estimated at sampled instants or continuously, depending on the capability of the recording, and the cadence is documented.

The protocol relates each level to expected, not guaranteed, observable effects. Longer episodes may increase the window in which the page is partially unavailable; broad movement may coincide with a change in posture and framing; central coverage may hide the active region of the stroke. These relationships are design hypotheses and will be examined per condition. The team measures detection availability, continuity, and recovery time after the hand leaves. It also reports the occluded fraction and its variation within the episode.

**Table 2.** Proposed metrics for evaluating detection, continuity, and recovery after the hand leaves, relating each measure to the observable definition and the corresponding limitation, without establishing an acceptance value.

| Metric | Definition | Unit or summary | Limitation |
|---|---|---|---|
| Occluded fraction | Covered area divided by page area | Ratio per observation or episode | Does not represent the importance of the covered region. |
| Availability | Episodes in which the page remains observable according to criterion | Proportion per condition | Depends on the external definition of presence. |
| Stroke continuity | Interruptions or discrepancies during and after coverage | Count, duration, or distance | Distinct measures should not be collapsed. |
| Recovery time | Interval between end of occlusion and return to availability | Time per episode | Depends on the rule for start and end. |
| Persistent failure | Absence of recovery until the end of the window | Count and proportion | Must separate end of observation from failure. |

![](figures/05-posturas-oclusao.svg)

**Figure 1.** Schematic postures in which the hand or instrument covers distinct parts of the page. The panels illustrate common conditions of use, not specific people or internal handling; author's own work.

![](figures/05-matriz-oclusao.svg)

**Figure 2.** Matrix of occlusion duration by page region, with cells reserved for conditions to be tested. The levels are qualitative and do not represent measurements or results; author's own work.

![](figures/05-fração-ocluida.svg)

**Figure 3.** Illustrative curve of the relationship between occluded fraction and performance, with axes without numbers. The expected shape is not a result and does not anticipate an empirical trend; author's own work.

Recovery time starts at the first instant at which the covered region ceases to be occluded according to independent annotation. Its end is the first observable response that satisfies the availability criterion, defined before the analysis. If there is no return within the window, persistent failure is recorded and time is not computed as if it were zero. The window and the censoring rule are described. Results are presented per episode and aggregated per participant, avoiding treating episodes from the same person as independent.

The analysis compares conditions with and without occlusion and stratifies by duration, movement, region, and fraction. The association between fraction and performance can be explored without presuming a linear form. Interactions are evaluated when planned and supported by the sample. Uncertainty intervals reflect clustering by session or participant. The team avoids interpreting a causal effect if the postures also alter the task, the stroke location, or the framing.

The analysis distinguishes the total region of the page from the region where the stroke is active. If both are annotated, the relationship between global coverage and coverage of the gesture can be described as two variables, without collapsing them. This distinction is useful when a small total fraction hides precisely the point of interaction, or when a large covered area is far from the stroke. The study records this information only if it can be annotated reliably.

A baseline without occlusion estimates behavior under visible conditions and contextualizes the measures. It does not represent the expectation that the hand disappear from the activity. Comparisons are paired by person and task when possible. If the occlusion duration varies widely, analyses by qualitative bands and by continuous fraction may be presented side by side. The protocol also reports episodes without recovery, instead of silently excluding the longest cases.

The protocol pre-specifies exclusions, treatment of uncertain occlusion, missing data, and episodes in which the person interrupts the activity. The occluded-fraction reference is independent of the system output. The conditions are described sufficiently for comparison, without revealing the internal mechanism. The recording, annotations, and analysis code are made available to the extent permitted by consent and privacy.

The analysis plan also defines how to deal with dependence between observations. One person may produce many episodes, and nearby episodes may share posture, rhythm, and context. The summary unit must be made explicit, with results per participant and per condition before any global aggregation. When modeling is used, the structure must acknowledge clustering and present uncertainty; the choice of model is justified by the design, without turning association into cause. Cases without a comparable event are described rather than removed without explanation.

The quality of the external reference needs to be examined separately from the response being evaluated. The protocol may use an independent assessment by annotators, a final digitization, or another measure appropriate to the task, provided the choice is documented and does not depend on the behavior one wishes to measure. A common sample of episodes makes it possible to discuss agreement and annotation limits. The report states whether the covered region was outlined manually and how doubts were resolved, but does not expose any internal mechanism of the system.

To interpret recovery time, the team must preserve the link between the coverage episode and the first response that becomes available again. A later event may be confused with recovery if the person changed activity or repositioned the page; therefore, context changes are annotated. Task interruption, absence of observation, and persistent failure are also distinguished. These categories protect the analysis against the practice of discarding precisely the episodes in which the response does not reappear within the observed window.

Finally, the protocol should record conditions that affect visibility without turning them into retrospective explanations. Illumination, cast shadow, paper orientation, and viewing distance may accompany changes in posture. When kept constant, they are described as conditions of the study; when they vary, they enter the record and the planned analysis. The goal is to allow readers to identify the scope of the evaluation, without implying that a single session represents all possible use.

## 5. Structure of the results

This section reserves the presentation format for a future evaluation. No experimental observations were provided for this article. Therefore, no performance values, differences between conditions, failure rates, or observed times are reported. Fields marked `[PENDING-DATA]` must be replaced only after collection, verification of the external reference, and documented analysis. The categories and metrics describe the plan; they do not anticipate the behavior of the system.

The first table should characterize the sample of episodes, including duration, movement, region, and occluded fraction. One row will indicate each planned condition, with the number of participants and sessions filled in after collection. The second table will present availability, continuity, recovery, and persistent failure. Each estimate will be accompanied by uncertainty and the aggregation rule. When a cell has no observations, the report will indicate absence of data instead of assigning a null value.

**Table 3.** Structure for reporting episodes by condition and observed coverage; the cells remain as collection fields until a reviewed sample exists and none of them represents a current result.

| Condition | Episodes | Occluded fraction | Valid observations |
|---|---|---|---|
| Duration and region | [PENDING-DATA] | [PENDING-DATA] | [PENDING-DATA] |
| Movement and region | [PENDING-DATA] | [PENDING-DATA] | [PENDING-DATA] |
| Condition without coverage | [PENDING-DATA] | Not applicable | [PENDING-DATA] |

A future figure may show distributions of continuity by category, always identifying participants and episodes. Another may relate occluded fraction to a previously defined metric and display uncertainty, avoiding smoothing that hides concentration of observations. Figure 3 of this article is only a schematic of a possible shape. There are no points, scales, or estimates in it; any empirical graph must come from verified data and be visually distinguished from the illustration.

## 6. Discussion

The protocol separates detection, continuity, and recovery because these responses may diverge. If the page remains available during coverage but the stroke shows interruptions, the finding would point to a difference between general availability and preservation of the graphic activity. If availability drops while the hand covers a small area, the position of the area may be more informative than the total fraction. If the output returns only after the hand leaves, the duration of the coverage and the recovery time would need to be interpreted together. These possibilities are not results of this article.

A pattern associated with duration, without a clear association with movement or region, would suggest that the observation window matters more than the trajectory of the hand in that drawing. This reading would still require checking whether long episodes coincide with pauses, greater task difficulty, or a change of posture. A relationship with broad movement could reflect joint displacement of the hand, the paper, or the framing. Therefore, external measures should be considered as a description of the episode and the causal conclusion must remain restricted to the experimental design.

An association with covered region may indicate that the location of the occlusion affects the usefulness of the output differently from the total amount of hidden area. Center and edge are not universal semantic categories: the region of the active stroke may cross both. Reporting the position of the ongoing drawing helps separate geometric location from relevance to the task. If the association disappeared when the stroke position was taken into account, this would suggest that the global fraction was an incomplete description, not that the earlier observation was wrong.

It is also possible that the categories show no discernible differences under the conditions evaluated. This pattern would not prove absence of effect in any situation. Interpretation would depend on the variety of postures, the resolution of the recording, the number and distribution of participants, and the accuracy of the external reference. A concentration of episodes in a single category would reduce the capacity for comparison. The report should present this imbalance and avoid turning lack of evidence into evidence of equivalence.

The proposed measures dialogue with the pen interaction literature, which treats the hand as a functional part of the action, and with research on digital surfaces that studies the conflict between visible content and occupied area [1–8]. Works on unintended touch and shadow tracking show why posture and region deserve their own description [10, 13, 14, 18]. The present protocol adds a temporal unit of episode and relates coverage to observable recovery; it does not propose an interface solution nor directly transfer the results of tabletop studies to paper.

The choice between natural task and instructed task involves a methodological trade-off. The natural task preserves spontaneous behavior but may not produce all combinations of the taxonomy. The guided task increases control but may lead participants to adopt uncommon postures. A two-part strategy may first record free activity and then request brief tasks for specific conditions. If adopted, the analysis keeps these blocks separate and reports how the instructions modified behavior. The study does not interpret ease of performing a requested pose as comfort or preference.

The use of image data requires additional caution. The hand, handwriting, and drawing habits may be identifiable or sensitive even without a face. The consent plan must explain recording, retention, access, and sharing. A public version may contain only derived annotations if the visual records cannot be distributed. This restriction reduces the possibility of independent re-annotation, so it must be considered when characterizing the strength of the evidence. Transparency about access limits is part of the report, not a flaw to conceal.

If recovery varies between tasks, the discussion should ask whether the chosen metric corresponds to what the person considers a useful return. Visual availability may be a necessary condition and still insufficient to resume drawing. Interviews or task observations could help interpret this mismatch in a later study, but do not replace operational annotation. The distinction between technical measure and meaning for the person prevents the team from attributing experiential value to an output change that was not evaluated with participants.

Taken together, the possible scenarios show why the article does not define an acceptable amount of occlusion. A universal value would ignore task, stroke position, instruction, and visual context. The protocol serves to organize observations that allow specific, justified decisions. The contribution lies in the comparability of descriptions and the explicit link between condition, response, and uncertainty; the existence and direction of any effect remain empirical questions.

## 7. Limitations and threats to validity

Construct validity depends on the categories representing relevant aspects of occlusion. Duration, movement, region, and fraction are observable descriptors, but they do not exhaust hand shape, pressure, postural preference, semantic importance of the stroke, or comfort. Classification into qualitative levels may hide variation within a category. The continuous measure of fraction reduces part of this loss, but also depends on the chosen time point and reference area. Future studies should justify these decisions in relation to the task.

The definition of continuity may also combine different phenomena. A visual interruption, a displaced mark, and a delayed return have distinct consequences. If they are summarized in a single measure, important differences may disappear. On the other hand, many metrics increase the chance of selective interpretation. The protocol should declare primary and secondary outcomes, explain how each is annotated, and present separate measures when their meanings are not equivalent. A definition that depends on the researcher's judgment must be accompanied by a manual and an agreement assessment.

Internal validity may be threatened by factors that change together with occlusion. Sheet movement, distance, shadow, gesture speed, and drawing difficulty may affect the observed response. An observational comparison describes association, but does not isolate cause. A controlled experiment may reduce confounding, at the cost of producing artificial postures. Alternation of conditions, pairing by person, recording of context, and pre-specified analysis help interpret results, without eliminating all ambiguity.

External validity is limited by the population, the type of paper, the instrument, and the capture environment. People with distinct drawing styles, dexterity, handedness preferences, and access needs may behave differently. A convenience sample does not allow generalizing to all users. The report should state who participated, how they were recruited, and which conditions were observed, preserving privacy. Replication in diverse contexts is necessary before formulating broad recommendations.

The quality of the external data may also limit interpretation. Insufficient resolution, shadows confused with the hand, edges outside the frame, and uncertain synchronization may shift the start and end of the episode. Annotators may disagree about partial coverage and the exact location of the active stroke. Temporal sampling may fail to capture brief occlusions. These problems should be quantified or described and not corrected through unrecorded assumptions. Sensitivity analysis may explore alternative annotation rules, if they are defined before observing the results.

There is also the risk of an observation effect: the recording or the instruction may alter posture and speed. If guided sessions are mixed with spontaneous drawing, the experimental condition may explain part of the difference. The protocol records the origin of each episode and presents separate strata. Even so, the presence of equipment and staff may change the interaction. This limitation does not invalidate the study, but restricts interpretation to documented conditions.

Finally, interpretation remains external to the evaluated system. A visible change does not identify the mechanism that produced it and should not be described as an internal cause. A black-box evaluation facilitates comparison of outcomes, but limits diagnoses and implementation recommendations. The data may support claims about observed episodes, not about all modes of operation nor about unmeasured mechanisms. This limit must accompany any future conclusion.

## 8. Conclusion

This article proposes evaluating natural hand and instrument occlusion during drawing by means of a taxonomy of duration, movement, and region, complemented by the fraction of the page covered. The protocol relates these descriptors to availability, stroke continuity, and recovery time after the coverage ends. Tables and figures organize the record without presenting nonexistent results.

The proposal maintains the distinction between observed condition and system response, considers natural and instructed tasks separately, and provides for explicit treatment of uncertainty, dependence between episodes, and privacy. The literature on pen, hand, digital paper, and shared surfaces motivates the dimensions, but does not determine effects for a specific scenario. Thus, no posture is classified beforehand as a failure or as acceptable.

The next step is to conduct an evaluation with participants, record episodes, and validate the independent annotations. Until such data exist, the relationship between the amount and location of coverage and performance remains `[PENDING-DATA]`. The results should fill the reserved fields, report uncertainty, and limit conclusions to the tasks and conditions actually observed.

## Statements

- AI use: text drafted with the support of generative AI, with review and responsibility of the authors; references checked by DOI.
- Data: there are no experimental data in this article; future results will be presented after collection and validation.
- Code: there is no analysis code associated with results in this version; future materials will be described with their version.
- Conflict of interest: the authors shall declare any relevant conflict before submission.
- Ethics: any study involving recording of participants will be submitted to the applicable ethical review before recruitment.
- Author contributions: the final version shall make the individual contributions of the authors explicit.

## References

[1] Vogel, D. et al. Hand occlusion with tablet-sized direct pen input. Proceedings of the SIGCHI Conference on Human Factors in Computing Systems, 2009. https://doi.org/10.1145/1518701.1518787
[2] Vogel, D.; Balakrishnan, R. Occlusion-aware interfaces. Proceedings of the SIGCHI Conference on Human Factors in Computing Systems, 2010. https://doi.org/10.1145/1753326.1753365
[3] Vogel, D.; Casiez, G. Hand occlusion on a multi-touch tabletop. Proceedings of the SIGCHI Conference on Human Factors in Computing Systems, 2012. https://doi.org/10.1145/2207676.2208390
[4] Vogel, D.; Balakrishnan, R. Direct Pen Interaction With a Conventional Graphical User Interface. Human–Computer Interaction, 2010. https://doi.org/10.1080/07370024.2010.499839
[5] Lee, J. et al. PhantomPen: Virtualization of pen head for digital drawing free from pen occlusion and visual parallax. Proceedings of the ACM Symposium on User Interface Software and Technology, 2012. https://doi.org/10.1145/2380116.2380159
[6] Brandl, P. et al. Occlusion-aware menu design for digital tabletops. CHI Extended Abstracts on Human Factors in Computing Systems, 2009. https://doi.org/10.1145/1520340.1520461
[7] Khalilbeigi, M. et al. Occlusion-aware interaction techniques for tabletop systems. CHI Extended Abstracts on Human Factors in Computing Systems, 2012. https://doi.org/10.1145/2212776.2223831
[8] Khalilbeigi, M. et al. ObjecTop: Occlusion awareness of physical objects on interactive tabletops. Proceedings of the ACM International Conference on Interactive Tabletops and Surfaces, 2013. https://doi.org/10.1145/2512349.2512806
[9] Kitani, K. et al. Toward the reduction of incorrect drawn ink retrieval. Human-centric Computing and Information Sciences, 2017. https://doi.org/10.1186/s13673-017-0099-0
[10] Annett, M. et al. Exploring and understanding unintended touch during direct pen interaction. ACM Transactions on Computer-Human Interaction, 2014. https://doi.org/10.1145/2674915
[11] Badam, S. K. et al. Tracing and sketching performance using blunt-tipped styli on direct-touch tablets. Proceedings of the International Working Conference on Advanced Visual Interfaces, 2014. https://doi.org/10.1145/2598153.2598182
[12] Aslan, I. et al. Exploring the user experience of proxemic hand and pen input above and aside a drawing screen. Proceedings of the International Conference on Mobile and Ubiquitous Multimedia, 2018. https://doi.org/10.1145/3282894.3282906
[13] Echtler, F. et al. Shadow tracking on multi-touch tables. Proceedings of the Working Conference on Advanced Visual Interfaces, 2008. https://doi.org/10.1145/1385569.1385640
[14] Isogawa, T. et al. Making graphical information visible in real shadows on interactive tabletops. IEEE Transactions on Visualization and Computer Graphics, 2014. https://doi.org/10.1109/TVCG.2014.2316002
[15] Rädle, R. et al. HuddleLamp: Spatially-aware mobile displays for ad-hoc around-the-table collaboration. Proceedings of the ACM International Conference on Interactive Tabletops and Surfaces, 2014. https://doi.org/10.1145/2669485.2669500
[16] Fujinawa, M. et al. Occlusion-aware hand posture based interaction on tabletop projector. Adjunct Publication of the ACM Symposium on User Interface Software and Technology, 2019. https://doi.org/10.1145/3332167.3356890
[17] Xu, C. et al. Recognizing unintentional touch on interactive tabletop. Proceedings of the ACM on Interactive, Mobile, Wearable and Ubiquitous Technologies, 2020. https://doi.org/10.1145/3381011
[18] Apitz, G.; Guimbretière, F. CrossY: A crossing-based drawing application. Proceedings of the ACM Symposium on User Interface Software and Technology, 2004. https://doi.org/10.1145/1029632.1029635
[19] Wu, C. et al. DodecaPen: Accurate 6DoF tracking of a passive stylus. Proceedings of the ACM Symposium on User Interface Software and Technology, 2017. https://doi.org/10.1145/3126594.3126664
[20] Jansen, C.; Sklar, E. Exploring co-creative drawing workflows. Frontiers in Robotics and AI, 2021. https://doi.org/10.3389/frobt.2021.577770
[21] Chen, X. et al. Two-handed drawing on augmented desk system. Proceedings of the Working Conference on Advanced Visual Interfaces, 2002. https://doi.org/10.1145/1556262.1556297
[22] Kim, H. J. et al. AR Pen and Hand Gestures: A New Tool for Pen Drawings. CHI Extended Abstracts on Human Factors in Computing Systems, 2013. https://doi.org/10.1145/2468356.2468525
[23] Aslan, I. et al. Pen + Mid-Air: An Exploration of Mid-Air Gestures to Complement Pen Input on Tablets. Proceedings of the Nordic Conference on Human-Computer Interaction, 2016. https://doi.org/10.1145/2971485.2971511
[24] Aslan, I. et al. Pen + Mid-Air Gestures: Eliciting Contextual Gestures. Proceedings of the ACM International Conference on Multimodal Interaction, 2018. https://doi.org/10.1145/3242969.3242979
[25] Maierhöfer, S. et al. TipTrack: Precise, low-latency, robust optical pen tracking on arbitrary surfaces using an IR-emitting pen tip. Proceedings of the International Conference on Tangible, Embedded, and Embodied Interaction, 2024. https://doi.org/10.1145/3623509.3633366
