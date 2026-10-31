# Portable agent workflow, version 7

This is a superseded version, kept as it ran. The current version is [v8](../v8/README.md), which has the full description, install and run instructions.

Version 7 changed version 6 in five ways, as described in the [method](../../method.md#ideal-setup-v7):
- it has one workflow for every model, with no `strong` or `guarded` profiles;
- step 0 fills `project.md` for a new project;
- it adds OpenSpec's requirement delta;
- it adds spec-kit's consistency read before building;
- it adds ponytail's "test each behaviour once" and caveman's terse working notes, used only in plans.

Its task-3 runs had two weaknesses that version 8 addresses:
- its "lowest level" rule displaced tests the project's own rules require;
- like the earlier versions, it did not look for existing requirements addressed to the change.
