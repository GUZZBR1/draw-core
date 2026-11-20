# Page identity continuity in drawing sessions

## Abstract

Maintaining a page’s identity throughout a session differs from detecting that a sheet is present in each observation. A page may remain, move, leave the scene temporarily, and return; other sheets may look similar or different. Inadequate decisions can associate drawings from distinct pages or interrupt continuity for the same page. This article proposes an event taxonomy for evaluating these decisions in a camera-assisted drawing system. The classification separates six observable events, three possible decisions—continue, create a distinct identity, or defer—and the consequences of incorrect merging and splitting. The protocol uses annotated sequences, qualitative variations in absence duration, and measures for correct re-identification, merging, splitting, and abstention. Evaluation treats the implementation as a black box and compares visible decisions with an independent reference. Tables and diagrams define events and costs without reporting measured performance. Since no experimental results are available, the article does not claim that any decision is correct in an existing system or define a waiting time. The proposal offers a basis for collecting and reporting continuity, uncertainty, and identity errors in drawing sessions.

**Keywords:** page identity; tracking; continuity; uncertainty; evaluation

## 1. Introduction

A drawing session may involve a single sheet that moves around or several similar sheets used in sequence. The camera may stop observing the page because of displacement, framing, an interruption in activity, or a change of support. When a sheet reappears, a decision must preserve continuity if it is the same page and avoid mixing content if it is another one. The situation seems simple while the page is always visible, but it becomes ambiguous in the face of absence and visual similarity.

It is useful to distinguish page detection from identity maintenance. The former asks whether there is an observable sheet at a given moment. The latter relates observations across the session and decides whether they belong to the same working object. An evaluation that counts only presence may classify as a success a sequence that associates marks from different sheets. Another that favors caution may repeatedly separate observations of the same page, fragmenting the history of the drawing. Both errors have distinct costs for continuity, integrity, and understanding of the content.

This article treats the problem as an external evaluation of a camera-assisted drawing system. Observable events and decisions that are communicated or inferable from the visible output are recorded. It does not describe how identity is computed, what internal evidence supports it, or for how long a decision is deferred. The question is: **how can page identity continuity be characterized in the face of displacement, absence, return, and the appearance of visually similar sheets?** The question covers both correctness and uncertainty, since deferring a decision may be preferable to merging distinct pages, depending on the task.

The article offers three contributions. First, it turns the generic expression “event taxonomy” into an explicit classification with six events, possible decisions, and consequences. Second, it separates incorrect merging, incorrect splitting, correct re-identification, and deferred decision. Third, it presents a protocol of annotated sequences that relates these outcomes to the observable duration of absence, keeping the implementation as a black box. These contributions define what to observe; they do not constitute evidence that a current system resolves the events.

Section 2 reviews tracking, re-identification, visual retrieval, and decision under uncertainty. Section 3 presents the taxonomy and makes explicit the costs of continuing, creating a distinct identity, or deferring. Section 4 describes sequences, annotation, measures, and analysis. Section 5 reserves structures for future results. Section 6 discusses possible interpretations and the relationship to the literature. Section 7 delimits validity and data, and Section 8 concludes by indicating the evidence needed.

The main unit is a transition between annotated observations within a session. Each transition receives a description of the previous state, the visible event, and the identity relation known to the reference. The reference may be defined by a discreet physical mark, session annotation, or another independent procedure, provided that it does not use the answer being evaluated as ground truth. Evaluators record ambiguous cases instead of deciding retrospectively in favor of a convenient interpretation.

The relevance of the question is not limited to a technical record. If two sheets are merged, marks may appear in the wrong context and the user may be unable to recover which drawing belongs to which support. If the same sheet is treated as new at each return, the history is fragmented and the task of resuming work may become confusing. A deferred decision also has a cost: it may require the person to wait or choose an additional action. These impacts must be examined without presuming that all errors are equally severe.

Visually similar pages are an important case, but not the only one. Two blank sheets may look identical; two drawings may share patterns; a different page may contain part of the same content if it was copied. Appearance alone does not define physical identity. For this reason, the protocol distinguishes reference ground truth from observable signals, and limits the conclusion to the way the study established that ground truth. The classification offers an evaluation language, not a universal theory of identity.

## 2. Related work

### 2.1 Tracking and re-identification

Object tracking relates observations of the same target along a sequence. In videos with multiple objects, the task includes detection, association between frames, and handling of entries into or exits from the field of view. The literature distinguishes localization errors from identity errors, since a target may remain visible while its association changes. Multi-object tracking metrics measure different aspects: correct correspondence, trajectory fragmentation, incorrect association, and identity consistency [1–6]. These distinctions are useful for evaluating sheets, provided that the unit and the reference ground truth are adapted to a drawing session.

Visual re-identification usually asks whether an object reappears in another image or after an interruption. Studies on people, vehicles, and scene objects offer strategies for dataset construction, trajectory annotation, and comparison of occurrences [7–12]. The page domain differs: paper may have little texture, sheets may be identical, and the drawn content changes during use. Therefore, results for people or vehicles do not directly inform the difficulty of re-identifying a page. The transferable value is conceptual: making explicit when the trajectory was interrupted, which instances could be confused, and how association errors are counted.

Tracking work also deals with occlusions, reappearance, pose changes, camera motion, and the entry of new targets. Not every disappearance means that the object has ceased to exist; it may have merely been hidden or lost by the framing. An annotated sequence should record this difference whenever the reference allows. In the drawing task, the sheet may be removed and brought back, but a cut in the recording or a momentarily covered page also creates an interval without observation. The protocol keeps these causes separate when known and records “unknown cause” when there is no evidence.

### 2.2 Page and image retrieval

Image retrieval seeks to locate visually related content in a collection. Document and handwritten-page retrieval systems study similarity of layout, text, marks, and regions. This field contributes ways of forming positive and negative pairs and the need to test repeated content. Even so, retrieving a similar image is not equivalent to confirming that the same physical sheet has returned. A copy, a reprinted page, or two similar supports may share content without being the same object. The physical reference must be defined independently [21–25].

Place recognition and visual localization address the return to a scene after changes in viewpoint, lighting, or time. These problems help in thinking about appearances that vary for the same place and about distinct environments that look the same. The page changes pose and content, but maintains a continuous physical relationship with the support. The comparison with visual localization serves to organize variation and ambiguity, not to import a metric without adaptation.

Benchmarks of photographed documents and collections of page images show how sequences and annotation can support comparison. The datasets vary in number of pages, type of writing, content repetition, capture, and available reference. The analysis must declare whether identity refers to the physical sheet, the logical document, or the version of the drawing. In this article, identity designates the physical support used in the session; content is the information drawn on it. This choice prevents identical copies from being automatically considered the same sheet.

### 2.3 Decision under uncertainty

Classification decisions may allow an abstention option when insufficient evidence does not support a choice. Studies on selective classification, calibration, and decision with asymmetric costs show why being right, being wrong, and not deciding are different outcomes. In an interaction, deferring may preserve safety, but it may also interrupt the flow or shift effort to the user. The literature offers models for comparing error cost and decision coverage; applying them to the return of a page requires defining the cost of each consequence in the context of the task.

Uncertainty management also depends on the temporal unit. A decision made in one observation may be revised when new evidence arrives, whereas a choice presented as final may affect subsequent content. The evaluation records the moment of the event and the visible decision, but does not infer internal rules. If the interface shows that the state is pending, this may be counted as abstention; if there is no observable signal, the study describes only the behavior that can be annotated.

The gap is to integrate the event taxonomy of a page with explicit decisions and costs in a drawing session. Tracking provides notions of fragmentation and association; image retrieval addresses similarity; decision studies address uncertainty and abstention. None of these lines, in isolation, defines the difference between merging two sheets and splitting the same sheet in the proposed task. The article combines these components to enable comparison without assuming how identity is computed.

Identity metrics involve distinct trade-offs. An association may be correct per frame and still fragment a long trajectory; a trajectory count may hide short periods of merging. Multi-object benchmarks and studies of temporal association show why correspondence, continuity, and identity switching need explicit definitions [4–13]. For pages, the denominator must exclude intervals without physical reference and report the frequency of each event, since rare sequences may dominate the uncertainty of an aggregate metric.

Work on content retrieval and person re-identification offers useful analogies, but its targets differ from the paper support. A person’s appearance may change with clothing, pose, and camera; a page changes with the drawing, folds, lighting, and position. Studies of local features and spatial matching help contextualize visual variation, while research on document duplicates reminds us that similarity is not the same as identity [14–26]. The protocol must declare whether it measures the same physical support or the same logical content.

## 3. Problem framing

Identity is defined here as continuity of the same physical support throughout the session. Appearance and content may vary without the sheet ceasing to be the same one; conversely, another sheet may look very similar. The protocol keeps the identity annotation separate from the decision being evaluated. Thus, the reference indicates which support is present, while the external response indicates whether continuity was preserved, a new identity was started, or the decision was left pending.

The taxonomy contains six events. **Remains** describes the page visible without a relevant transition in physical identity. **Moves** records a change of position or pose while the same sheet remains in the session. **Disappears** indicates that the sheet stops being observed for an interval, without concluding that it was discarded. **Returns** is the reappearance of the same physical sheet after absence. **Another similar one appears** describes the entry of a distinct support with an appearance similar to the previous page. **Another different one appears** describes the entry of a visually distinguishable support. The cause of absence and the degree of similarity are annotated separately when the reference allows.

The possible decisions are **continue**, **new**, and **defer**. Continue maintains the relation with the previous identity. New starts a distinct identity. Defer records that the observable evidence was considered insufficient to choose between the two relations. These labels describe an external decision; they do not reveal how it was produced. When the interface does not make the decision explicit, evaluators may derive it from the visible output only if the annotation rule is defined and can be applied without reconstructing internal details.

A correct decision depends on the event and the reference. For a page that remains or moves, continuing preserves the trajectory. After disappearance and return of the same sheet, continuing is a correct re-identification. If another sheet appears, starting a new identity avoids merging. A deferred decision is not automatically correct or incorrect: it represents abstention, whose cost must be reported. In the analysis, abstentions are separated from merging and splitting errors, and it is also examined whether they are concentrated in difficult events.

**Table 1.** Taxonomy of page events, possible decisions, and consequences of continuing, creating a distinct identity, or deferring an uncertain decision, considering the physical reference independent of the output observed in the session.

| Reference event | Continue | New identity | Defer |
|---|---|---|---|
| Remains | Correct continuity | Incorrect splitting of the same sheet | Abstention with no apparent need |
| Moves | Correct continuity | Fragmentation of the trajectory of the same sheet | Temporary interruption for analysis |
| Disappears | Continuity state not observable during the absence | Premature new identity if the sheet returns | Abstention until a new observation |
| Same sheet returns | Correct re-identification | Incorrect splitting of the same sheet | Unresolved continuity |
| Another similar one appears | Incorrect merging of distinct sheets | Correct new identity | Abstention in the face of similarity |
| Another different one appears | Incorrect merging of distinct sheets | Correct new identity | Avoidable abstention if the distinction is clear |

The cost is asymmetric and depends on the application. In a session that preserves each page as a unit of work, a merge may attribute marks to the wrong support; in a task that expects continuity, a split may require manual recovery. The team declares which consequence has priority and keeps the metrics independent so that another study can apply different costs. No universal rule turns the two errors into a single penalty.

An **incorrect merging** occurs when observations of distinct physical sheets are associated with a single identity. Its cost may include mixing of marks, wrong attribution of history, and confusion when resuming the session. An **incorrect splitting** occurs when the same sheet receives distinct identities after displacement or return. Its cost includes fragmentation of the history and loss of continuity. Neither of these errors should be summarized merely as “incorrect identity,” since their consequences and frequencies may differ.

The taxonomy also distinguishes the uncertain event from the deferred decision. The reference annotation may be ambiguous because the recording does not allow knowing whether the sheet returned or another similar one entered. In this case, the transition is marked as uncertain and no correct or incorrect decision is assigned without evidence. A deferred decision, by contrast, is a response observed in the face of an event whose reference identity is known. This difference avoids treating evaluator uncertainty as system abstention.

Visual similarity is graded qualitatively and separated from physical identity. The categories “similar” and “different” must have examples in the manual, but they do not presuppose an internal measure of similarity. If the team cannot distinguish the classes consistently, it may report appearance through independent annotation and run a sensitivity analysis. The category is not based on confidential textual content or on internal characteristics not visible to the researcher.

The decision may have consequences beyond the label. A merge may add marks from one page to the history of another, whereas a split may require the person to manually recover the previous drawing. The evaluation annotates observable effects on content or interaction, but does not presume that every error causes irreversible loss. The cost depends on what the session allows to be corrected, on the context of use, and on the person’s expectation. These effects are measured as secondary outcomes, without replacing the identity classification.

Figure 1 represents a session with permanence, displacement, absence, appearance of a similar page, and return. The order in the diagram is merely illustrative; real events may occur in another sequence. Figure 2 shows events, decisions, and consequence classes without indicating internal computation. Figure 3 reserves an illustrative form for examining error according to the observable duration of absence. No figure reports internal processing or measured performance.

![](figures/03-timeline-identidade.svg)

**Figure 1.** Conceptual timeline with permanence, displacement, absence, return, and observation of similar pages, without indicating an internal rule or processing; the milestones are observable events; author's own work.

## 4. Proposed evaluation protocol

The protocol uses annotated sequences of sessions with one or more pages. Each session contains periods of permanence and displacement, absences with a known cause when possible, return of the same sheet, and entry of distinct sheets. Conditions with visually similar pages are included if they are part of the question, without presuming that every similarity produces ambiguity. The observable duration of absence varies between sessions or blocks to allow analysis of its association with errors, but the study does not describe internal parameters.

A capture script describes the task, the physical change of page, the framing, and the way of marking the reference. Identity ground truth may be established by an observer who follows the session, by an external mark not visible to the evaluated output, or by an independent record. The marking cannot depend on the observed decision. If the support leaves the frame and its identity ceases to be known, the episode is labeled as indeterminate. The recordings are evaluated by trained annotators who, whenever possible, do not see the aggregated response of the condition.

The set of conditions crosses reference event, similarity between pages, qualitative duration of absence, and movement state. The matrix should prioritize balanced coverage instead of producing all combinations, which may be numerous. The order is alternated or randomized to reduce confounding with learning and fatigue. Spontaneous and instructed sessions are identified separately; an induced situation is not treated as equivalent to a natural return.

The metrics have explicit denominators. **Correct re-identification** is the number of returns of the same sheet associated with the reference identity, divided by the returns whose identity can be annotated. **Incorrect merging** counts events in which distinct sheets share an identity, with the denominator of known appearances of new sheets. **Incorrect splitting** counts new identities assigned to the same sheet, using transitions in which physical continuity was confirmed. **Abstention** reports deferred decisions by event type. The unit may be event, trajectory, or session; the report presents the unit consistently.

**Table 2.** Metrics for correct re-identification, incorrect merging, and incorrect splitting, with declared denominators and separate treatment of abstention and cases without a reliable reference, facilitating comparison across evaluated sessions.

| Metric | Definition | Denominator | Interpretation |
|---|---|---|---|
| Correct re-identification | Return of the same sheet associated with the reference identity | Returns with known reference | Continuity preserved after absence |
| Incorrect merging | Distinct sheets associated with the same identity | Distinct appearances with known reference | Mixing of sheet histories |
| Incorrect splitting | Same sheet represented as different identities | Transitions with confirmed continuity | Fragmentation of the history |
| Abstention | Explicitly deferred decision | Events with observable decision | Uncertainty transferred or preserved |
| Indeterminate case | Reference does not allow identifying the sheet | Events without reliable reference | Excluded from the accuracy rate and reported separately |

The analysis presents a confusion matrix between decision and reference, complemented by frequencies of merging, splitting, and abstention. For trajectories, fragmentations and incorrect associations per session are reported, without treating each correlated frame as an independent observation. Results are aggregated by participant and session when these groupings exist. Uncertainty intervals reflect the actual sampling unit. Indeterminate cases remain visible in the report and are not silently removed.

The association between absence duration and error is explored through predefined categories and through a continuous distribution when the timestamp can be annotated. The analysis does not presume an increasing relationship, nor does it turn an illustrated trend into a confirmed hypothesis. If the sample is small in certain categories, this will be reported as limited coverage. The comparison between visual similarity and error also considers page order and task context, without inferring that similarity was used by any internal component.

The protocol may evaluate the interaction cost of a deferred decision, such as an observable interruption or a request for an additional action, provided that the output allows this effect to be measured. A later interview may ask whether the perceived continuity matched the task, but this perception does not replace the physical reference. Technical metrics and participant reports are analyzed separately and related only with a declared method.

The annotation manual defines event, physical identity, similarity, start and end of absence, and evidence for a visible decision. A sample of the sequences is annotated by two people to examine agreement. Disagreements are preserved until adjudication and used to identify ambiguous categories. The team reports missing data, cuts in the recording, and task changes. Figure 1 offers a conceptual timeline; Figure 2 summarizes the external relationship between event, decision, and cost; and Figure 3 presents only a potential form of chart.

The plan pre-registers which events count as eligible, how the session is ended, and how incomplete sequences are handled. A page that leaves the field without a later reference cannot be evaluated as a correct or incorrect return. A capture failure that erases the entire interval is distinct from a physical exit of the page. Categories that cannot be determined are kept visible in the exclusion flow, so that collection uncertainty is not confused with a system decision.

The protocol also separates association quality from impact on the activity. A confusion matrix characterizes correspondence; a task or interview may characterize effects on resumption and understanding. When both are collected, they are analyzed in layers: first the relationship with the physical reference, then the reported experience. The association between the two does not demonstrate cause and may depend on familiarity, expectation, or the possibility of correcting the error.

![](figures/03-decisoes-identidade.svg)

**Figure 2.** Conceptual diagram relating observed events to possible decisions and costs of association or separation; the arrows do not represent internal processing in the evaluated implementation; author's own work.

![](figures/03-erro-ausencia.svg)

**Figure 3.** Illustrative curve of the relationship between absence duration and identity error, without a numerical scale. The expected shape is not a result, but merely a conceptual diagram; author's own work.

## 5. Structure of the results

This section reserves the presentation format for a future evaluation. No observed sequence or decision was provided; therefore, there are no re-identification, merging, splitting, or abstention rates. The fields marked `[PENDING-DATA]` will be filled in only after independent annotation and review of the indeterminate cases. The tables describe what is to be reported, not predicted results.

The report begins with the composition of the sample: sessions, distinct physical pages, returns, new appearances, and reference events by class. Categories with no occurrence will be identified as not observed, instead of receiving a zero rate. The absence duration will be shown as a distribution of events, with reference to the time unit and the annotation rule used. Uncertain reference cases will be counted separately to prevent coverage from appearing larger than the available information.

**Table 3.** Structure for reporting annotated events and observed decisions, keeping fields empty until the sequences have been collected and reviewed by independent evaluators, without any observed result.

| Event | Cases with reference | Observed decisions | Annotation notes |
|---|---|---|---|
| Permanence or displacement | [PENDING-DATA] | [PENDING-DATA] | [PENDING-DATA] |
| Absence and return of the same sheet | [PENDING-DATA] | [PENDING-DATA] | [PENDING-DATA] |
| Appearance of another sheet | [PENDING-DATA] | [PENDING-DATA] | [PENDING-DATA] |
| Indeterminate reference | [PENDING-DATA] | Not applicable | [PENDING-DATA] |

The main results should show correct re-identification, incorrect merging, incorrect splitting, and abstention with their denominators. The matrix between event and decision makes it easier to identify whether errors are concentrated in return, similarity, or page change. For sequences with several transitions, fragmentation per session will complement the count per event. Uncertainty will be reported according to the grouping by person or session; correlated observations will not be counted as if they were distinct participants.

A future figure may relate error to the observable duration of absence, provided that the sample covers different intervals and the design does not confound duration with page identity or capture condition. Figure 3 is merely an illustrative form and does not imply an increasing relationship. If the empirical pattern is not monotonic, the visualization should reflect that. Results without identity recovery will be described as such, without attributing an internal rule to explain the case.

## 6. Discussion

A predominance of correct re-identifications after return would indicate continuity in the evaluated sequences and conditions, but would not demonstrate that identity was preserved in any scenario. The reading would depend on the variety of pages, the observed duration of absence, the rate of similar pages, and the quality of the reference. A sequence composed only of visually distinct sheets would test a simpler problem than the encounter with similar pages. The composition of the sample must accompany any performance summary.

If incorrect merges were concentrated when another similar page appears, the finding would point to the sensitivity of the association to visual ambiguity in the observed conditions. Even so, the interpretation must consider capture order, content, pose, and physical annotation. The result would not reveal which visual attribute was used, nor would it authorize recommending an internal solution. It could justify new studies with controlled pairs of pages or with natural variations of content.

If incorrect splits were more common after the return of the same sheet, the continuity of the session would be being fragmented under some conditions. The consequence may be more or less serious depending on whether the person can recover the previous drawing through an explicit action. The analysis must distinguish technical fragmentation from participants’ perception of loss. A decision to start a new identity may be prudent in uncertain cases and still impose a resumption cost; for this reason, technical and interaction metrics are reported together, without being confused.

Abstentions may reduce merges and splits, but may also interrupt the task or require a confirmation. A result with fewer errors and more deferred decisions is not automatically superior or inferior. The comparison depends on cost, frequency, and possibility of recovery, aspects related to use. Studies of selective decision and uncertainty motivate reporting coverage together with error, instead of hiding abstentions in an aggregate rate [13, 20]. The team should describe what the person sees and does after the pending decision, if this is observable.

An association between absence duration and error may be plausible, but it is not inevitable. A longer period may coincide with a page change, a change of activity, or changes in the environment. A brief absence may occur precisely during an intentional change of support. The protocol annotates these events to avoid interpreting duration in isolation. If there is insufficient coverage per category, the discussion should be limited to description, without extrapolating a curve to absent times.

Multi-object tracking offers concepts such as trajectory fragmentation, identity switching, and correct association. Such concepts help separate errors that a simple presence measure would not detect. However, benchmark metrics are defined for frames and targets with their own conditions. This protocol adopts the conceptual distinctions and recomputes denominators with the physical page and the session as the relevant units. Direct transfer of rankings or values from other domains would be unjustified.

Visual retrieval may relate similar pages or images, but physical identity is not reducible to content similarity. A copy of the same drawing on another sheet represents another instance for this article. This scoping must be explicit, especially when document banks treat versions or logical pages as identity. If an application defines identity by content rather than by support, it will be necessary to change the reference and interpret the costs differently.

The possible results also need to be seen from the perspective of use. A merge may confuse authorship or history, whereas a split may fragment the drawing and require manual navigation. The importance depends on task, reversibility, and possibility of correction. Studies with participants could evaluate whether pending decisions are understandable and whether errors affect trust. Such a later study should not infer experience from technical counts, since a rare occurrence may have high impact and a frequent occurrence may be easily corrected.

Finally, no acceptable duration of absence is defined. The tracking literature may suggest conditions and comparison measures, but the appropriate interval depends on speed of use, interaction, and the cost of each decision. The contribution of this proposal is to ensure that absence, return, and identity are described before a performance judgment is presented. Standards and recommendations can only emerge from observed data and tasks.

## 7. Limitations and threats to validity

Construct validity depends on the definition of physical identity and on the annotated events. The classification “similar page” is subjective if there are no clear instructions; “return” may be confused with another instance without an external mark; and “absence” may result from a cut in the recording rather than real movement. The protocol separates these cases and uses an indeterminate category, but the annotation remains dependent on the quality and continuity of the record.

The metrics may favor one type of error. An aggregate accuracy rate may appear high even when merges have severe consequences or when abstentions are concentrated in frequent conditions. Counts with different denominators should not be compared without explanation. The team chooses primary outcomes in advance, reports raw frequencies and uncertainty, and presents the distribution by event. The analysis of fragmentation per session complements the per-transition measure, but does not replace it.

Internal validity is threatened by co-occurrence between absence and page change, similarity and content, or pose and displacement. A controlled manipulation may isolate part of these factors, but reduce the naturalness of the task. A spontaneous observation preserves use, but does not support the same causal inference. The design must state which question it intends to answer and limit the language of the conclusions to the type of comparison performed.

External validity depends on sheet types, drawing, session duration, capture method, and participant diversity. Blank pages, sheets with dense content, and drawings in progress may present different challenges. An evaluation done on a stable desk does not automatically represent other surfaces or contexts. The study must describe the population and the environment and avoid the claim that the taxonomy covers all uses.

The quality of the reference may be the main source of error. A physical mark or in-person monitoring helps establish identity, but may fail if sheets are swapped outside the record. Annotators may disagree about the same page when the sequence has cuts or partial framing. Agreement and adjudication must be reported; sequences without reliable ground truth are excluded from the accuracy metrics and presented as indeterminate. An imperfect reference also limits the apparent precision of the evaluated system.

There is also temporal dependence. Frames close together in the same session share context and are not equivalent to independent observations. Ignoring the grouping may artificially narrow uncertainty. An uneven sample, with many sequences from few people, may appear large without representing real diversity. The analysis must make explicit the experimental unit, the annotation unit, and the statistical grouping.

Finally, the black-box protocol measures external outputs and does not explain how continuity is produced. A wrong association may result from several factors that the evaluation does not separate. This restriction preserves the possibility of comparison without disclosing internal details, but reduces diagnosis and the proposal of corrections. Conclusions about the mechanism or computation of identity are not supported by this design.

## 8. Conclusion

This article proposes a taxonomy for evaluating page identity throughout drawing sessions. Six events—permanence, displacement, absence, return of the same sheet, appearance of another similar one, and appearance of another different one—are related to the decisions to continue, start a distinct identity, or defer. The classification separates correct re-identification, incorrect merging, incorrect splitting, abstention, and indeterminate reference.

The protocol uses annotated sequences and an independent physical reference. It compares observable decisions with the known identity, describes absence duration as an external condition, and keeps the implementation as a black box. Tables and figures organize events and costs without presenting data. Future results should show denominators, uncertainty, grouping, and consequences for the task.

An evaluation with varied sheets, return events, and visually similar pages is still needed. Validation of the annotation and analysis of decision costs are essential before any recommendation. Until then, the relationship between absence, similarity, and error remains `[PENDING-DATA]`.

## Statements

- AI use: text drafted with the support of generative AI, with review and responsibility of the authors; references checked by DOI.
- Data: there are no experimental data in this proposal; future sequences and results will be described after collection and validation.
- Code: there is no results-analysis code in this version; future materials will be identified by version.
- Conflict of interest: the authors shall declare any relevant conflict before submission.
- Ethics: studies with participants and session recordings will be submitted to the applicable ethical review before recruitment.
- Author contributions: the final version shall make the individual contributions of the authors explicit.

## References

[1] Kuhn, H. W. The Hungarian Method for the Assignment Problem. Naval Research Logistics Quarterly, 1955. https://doi.org/10.1002/nav.3800020109
[2] Reid, D. An Algorithm for Tracking Multiple Targets. IEEE Transactions on Automatic Control, 1979. https://doi.org/10.1109/TAC.1979.1102177
[3] Blackman, S. S. Multiple Hypothesis Tracking for Multiple Target Tracking. IEEE Aerospace and Electronic Systems Magazine, 2004. https://doi.org/10.1109/MAES.2004.1263228
[4] Joo, S.-W.; Chellappa, R. A Multiple-Hypothesis Approach for Multiobject Visual Tracking. IEEE Transactions on Image Processing, 2007. https://doi.org/10.1109/TIP.2007.906254
[5] Cox, I. J.; Hingorani, S. L. An Efficient Implementation of Reid’s Multiple Hypothesis Tracking Algorithm and Its Evaluation for the Purpose of Visual Tracking. IEEE Transactions on Pattern Analysis and Machine Intelligence, 1996. https://doi.org/10.1109/34.481539
[6] Bernardin, K.; Stiefelhagen, R. Evaluating Multiple Object Tracking Performance: The CLEAR MOT Metrics. EURASIP Journal on Image and Video Processing, 2008. https://doi.org/10.1155/2008/246309
[7] Dendorfer, P. et al. MOTChallenge: A Benchmark for Single-Camera Multiple Target Tracking. International Journal of Computer Vision, 2021. https://doi.org/10.1007/s11263-020-01393-0
[8] Ristani, E. et al. Performance Measures and a Data Set for Multi-Target, Multi-Camera Tracking. European Conference on Computer Vision Workshops, 2016. https://doi.org/10.1007/978-3-319-48881-3_2
[9] Luiten, J. et al. HOTA: A Higher Order Metric for Evaluating Multi-object Tracking. International Journal of Computer Vision, 2021. https://doi.org/10.1007/s11263-020-01375-2
[10] Bewley, A. et al. Simple Online and Realtime Tracking. International Conference on Image Processing, 2016. https://doi.org/10.1109/ICIP.2016.7533003
[11] Wojke, N.; Bewley, A.; Paulus, D. Simple Online and Realtime Tracking with a Deep Association Metric. International Conference on Image Processing, 2017. https://doi.org/10.1109/ICIP.2017.8296962
[12] Zhang, Y. et al. ByteTrack: Multi-object Tracking by Associating Every Detection Box. European Conference on Computer Vision, 2022. https://doi.org/10.1007/978-3-031-20047-2_1
[13] Vo, B.-N.; Vo, B.-T.; Phung, D. Labeled Random Finite Sets and the Bayes Multi-Target Tracking Filter. IEEE Transactions on Signal Processing, 2014. https://doi.org/10.1109/TSP.2014.2364014
[14] Bedagkar-Gala, A.; Shah, S. K. A Survey of Approaches and Trends in Person Re-Identification. Image and Vision Computing, 2014. https://doi.org/10.1016/j.imavis.2014.02.001
[15] Ye, M. et al. Deep Learning for Person Re-Identification: A Survey and Outlook. IEEE Transactions on Pattern Analysis and Machine Intelligence, 2022. https://doi.org/10.1109/TPAMI.2021.3054775
[16] Zheng, L. et al. Scalable Person Re-Identification: A Benchmark. IEEE/CVF International Conference on Computer Vision, 2015. https://openaccess.thecvf.com/content_iccv_2015/html/Zheng_Scalable_Person_Re-Identification_ICCV_2015_paper.html
[17] Zheng, L. et al. Person Re-identification in the Wild. IEEE/CVF Conference on Computer Vision and Pattern Recognition, 2017. https://doi.org/10.1109/CVPR.2017.357
[18] Gou, M. et al. DukeMTMC4ReID: A Large-Scale Multi-camera Person Re-identification Dataset. IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops, 2017. https://doi.org/10.1109/CVPRW.2017.185
[19] Zheng, L. et al. MARS: A Video Benchmark for Large-Scale Person Re-Identification. European Conference on Computer Vision, 2016. https://doi.org/10.1007/978-3-319-46466-4_52
[20] Yu, T. et al. Robust Person Re-Identification by Modelling Feature Uncertainty. IEEE/CVF International Conference on Computer Vision, 2019. https://doi.org/10.1109/ICCV.2019.00064
[21] Lowe, D. G. Distinctive Image Features from Scale-Invariant Keypoints. International Journal of Computer Vision, 2004. https://doi.org/10.1023/B:VISI.0000029664.99615.94
[22] Bay, H. et al. Speeded-Up Robust Features (SURF). Computer Vision and Image Understanding, 2008. https://doi.org/10.1016/j.cviu.2007.09.014
[23] Sivic, J.; Zisserman, A. Video Google: A Text Retrieval Approach to Object Matching in Videos. IEEE/CVF International Conference on Computer Vision, 2003. https://doi.org/10.1109/ICCV.2003.1238663
[24] Philbin, J. et al. Object Retrieval with Large Vocabularies and Fast Spatial Matching. IEEE/CVF Conference on Computer Vision and Pattern Recognition, 2007. https://doi.org/10.1109/CVPR.2007.383172
[25] Conrad, J. G.; Schriber, C. P. Managing déjà vu: Collection Building for the Identification of Nonidentical Duplicate Documents. Journal of the American Society for Information Science and Technology, 2006. https://doi.org/10.1002/asi.20363
[26] Dicle, C.; Camps, O. I.; Sznaier, M. The Way They Move: Tracking Multiple Targets with Similar Appearance. IEEE/CVF International Conference on Computer Vision, 2013. https://openaccess.thecvf.com/content_iccv_2013/papers/Dicle_The_Way_They_2013_ICCV_paper.pdf
