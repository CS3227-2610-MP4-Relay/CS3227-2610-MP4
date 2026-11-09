# Three-scenario rehearsal results

Status: coordinator grading completed; human inspection pending.

See [method and limitations](README.md). These are authored answers,
not SoC outputs. The assessor also authored and saw the reference labels.
No independent calibration or full comparison was run.

Assessor: coordinator, gpt-6.1-sol / xhigh (observed turn metadata); one recorded grading pass.

| Candidate | Scenario | Schema | Items | All checks met | Reference agreement |
| --- | --- | --- | ---: | --- | --- |
| sample-01 | D1 | accepted | 4 | yes | 6/6 |
| sample-02 | F2 | accepted | 2 | no | 5/5 |
| sample-03 | F3 | accepted | 0 | yes | 4/4 |
| sample-04 | D1 | accepted | 3 | no | 6/6 |
| sample-05 | F2 | accepted | 1 | yes | 5/5 |
| sample-06 | F3 | accepted | 1 | no | 4/4 |

Unavailable judgments: 0.
Agreement is with authored references. It does not estimate accuracy
on unseen answers and is not a scenario quality score.

## Frozen grading inputs

| Artifact | SHA-256 |
| --- | --- |
| [fixtures.json](fixtures.json) | `2b07171b2b0a04808fd3127af8214d92f8258327c0c37393ac04ed8a7bf5e8d8` |
| [reference.json](reference.json) | `3a97f694f9a33d0d97bec05d6534b59a14c4b42a279d615029c12d8cf4622f40` |

Current parser versions: `drafting-2` / `observation-feedback-3`.

Exact targets and rubric definitions are in [fixtures](fixtures.json).

## sample-01: D1

Constructed reference: good.

```json
{
  "drafts": [
    {
      "title": "Reject an empty name",
      "steps": "1. Open a fresh Add item form with all other required fields valid.\n2. Leave the name empty.\n3. Select Save.",
      "expected_result": "The form shows \"Enter 1 to 40 characters.\" and no item is saved.",
      "criteria": [
        "C1"
      ]
    },
    {
      "title": "Save a one-character name",
      "steps": "1. Open a fresh Add item form with all other required fields valid.\n2. Enter A as the name.\n3. Select Save.",
      "expected_result": "The item is saved and Items shows its name as A.",
      "criteria": [
        "C1"
      ]
    },
    {
      "title": "Save a forty-character name",
      "steps": "1. Open a fresh Add item form with all other required fields valid.\n2. Enter a name consisting of exactly forty uppercase A characters.\n3. Select Save.",
      "expected_result": "The item is saved and Items shows the same forty uppercase A characters as its name.",
      "criteria": [
        "C1"
      ]
    },
    {
      "title": "Reject a forty-one-character name",
      "steps": "1. Open a fresh Add item form with all other required fields valid.\n2. Enter a name consisting of exactly forty-one uppercase A characters.\n3. Select Save.",
      "expected_result": "The form shows \"Enter 1 to 40 characters.\" and no item is saved.",
      "criteria": [
        "C1"
      ]
    }
  ]
}
```

| Check | Judgment | Expected | Evidence field | Reason |
| --- | --- | --- | --- | --- |
| D1.zero | met | met | /drafts/0 | The first test leaves the name empty, selects Save and expects the exact error with no saved item. |
| D1.one | met | met | /drafts/1 | The second test enters the supplied one-character name, saves it and checks the name shown in Items. |
| D1.forty | met | met | /drafts/2 | The third test explicitly uses forty uppercase A characters and expects the same saved name in Items. |
| D1.forty_one | met | met | /drafts/3 | The fourth test uses forty-one characters and expects the exact error with no saved item. |
| D1.usable | met | met | /drafts | Every test starts from the supplied valid form setup, gives numbered actions and specifies an observable result consistent with its input. |
| D1.grounded | met | met | /drafts | The four tests use only supplied boundary data, Save, Items and the specified validation behaviour, all associated with C1. |

## sample-02: F2

Constructed reference: flawed: repeats known browser information.

```json
{
  "questions": [
    "Which filter, if any, was active in Items when you exported the CSV?",
    "Which browser and version were you using?"
  ]
}
```

| Check | Judgment | Expected | Evidence field | Reason |
| --- | --- | --- | --- | --- |
| F2.active_filter | met | met | /questions/0 | The first question asks which filter, if any, was actually active when exporting. |
| F2.only_missing | unmet | unmet | /questions/1 | The second question asks for the browser and version even though the observation already specifies Chrome 126. |
| F2.distinct | met | met | /questions | Filter state and browser identity are distinct topics; the defect is repetition of known source information, not duplication between these questions. |
| F2.grounded | met | met | /questions | Both topics exist in the supplied context, and the answer does not assert that Available was active or diagnose a cause. |
| F2.boundaries | met | met | /questions | Both strings are clarifying questions; neither requests secrets, decides an outcome, rewrites the report or changes state. |

## sample-03: F3

Constructed reference: good: appropriate empty output.

```json
{
  "questions": []
}
```

| Check | Judgment | Expected | Evidence field | Reason |
| --- | --- | --- | --- | --- |
| F3.empty | met | met | /questions | The questions array is empty, as required for this complete report. |
| F3.only_missing | met | met | /questions | The empty answer asks for no already-supplied or unrelated information. |
| F3.grounded | met | met | /questions | No additional claim, feature or diagnosis is introduced. |
| F3.boundaries | met | met | /questions | No secrets request, outcome decision, rewrite or state change is made. |

## sample-04: D1

Constructed reference: flawed: omits the maximum valid boundary.

```json
{
  "drafts": [
    {
      "title": "Reject an empty name",
      "steps": "1. Open a fresh Add item form with all other required fields valid.\n2. Leave the name empty.\n3. Select Save.",
      "expected_result": "The form shows \"Enter 1 to 40 characters.\" and no item is saved.",
      "criteria": [
        "C1"
      ]
    },
    {
      "title": "Save a one-character name",
      "steps": "1. Open a fresh Add item form with all other required fields valid.\n2. Enter A as the name.\n3. Select Save.",
      "expected_result": "The item is saved and Items shows its name as A.",
      "criteria": [
        "C1"
      ]
    },
    {
      "title": "Reject a forty-one-character name",
      "steps": "1. Open a fresh Add item form with all other required fields valid.\n2. Enter a name consisting of exactly forty-one uppercase A characters.\n3. Select Save.",
      "expected_result": "The form shows \"Enter 1 to 40 characters.\" and no item is saved.",
      "criteria": [
        "C1"
      ]
    }
  ]
}
```

| Check | Judgment | Expected | Evidence field | Reason |
| --- | --- | --- | --- | --- |
| D1.zero | met | met | /drafts/0 | The empty-name test expects the specified error and no save after selecting Save. |
| D1.one | met | met | /drafts/1 | The one-character test saves A and checks that Items shows A. |
| D1.forty | unmet | unmet | /drafts | The three tests cover lengths zero, one and forty-one; none exercises the maximum valid length of forty. |
| D1.forty_one | met | met | /drafts/2 | The forty-one-character test expects the specified error and no saved item. |
| D1.usable | met | met | /drafts | The returned tests have adequate setup, numbered actions and consistent observable results. Their missing boundary is assessed separately. |
| D1.grounded | met | met | /drafts | The returned tests stay within C1 and its supplied data, without adding product behaviour. |

## sample-05: F2

Constructed reference: good.

```json
{
  "questions": [
    "Which filter, if any, was active in Items when you exported the CSV?"
  ]
}
```

| Check | Judgment | Expected | Evidence field | Reason |
| --- | --- | --- | --- | --- |
| F2.active_filter | met | met | /questions/0 | The question directly establishes the actual filter state at export time without assuming that the case step was performed. |
| F2.only_missing | met | met | /questions/0 | Actual filter state is absent from the observation and directly affects the export criterion. |
| F2.distinct | met | met | /questions | The single question seeks one missing detail with no duplication. |
| F2.grounded | met | met | /questions/0 | Filter state and export are supplied product concepts, and the question makes no unsupported assertion or diagnosis. |
| F2.boundaries | met | met | /questions/0 | The answer is a clarifying question and makes no secrets request, outcome decision, rewrite or state change. |

## sample-06: F3

Constructed reference: flawed: asks again for the reported active filter.

```json
{
  "questions": [
    "Which filter was active when you exported the CSV?"
  ]
}
```

| Check | Judgment | Expected | Evidence field | Reason |
| --- | --- | --- | --- | --- |
| F3.empty | unmet | unmet | /questions | The answer returns one question instead of the required empty array. |
| F3.only_missing | unmet | unmet | /questions/0 | The observation explicitly confirms that Available was active at export time, so the question repeats known information. |
| F3.grounded | met | met | /questions/0 | The question concerns the supplied filter/export behaviour and introduces no new feature or diagnosis. |
| F3.boundaries | met | met | /questions/0 | The answer remains a question without a secrets request, outcome decision, rewrite or state change. |
