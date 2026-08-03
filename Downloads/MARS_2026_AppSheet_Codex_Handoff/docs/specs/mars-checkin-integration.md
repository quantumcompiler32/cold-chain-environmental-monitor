# MARS Form, Roster, and AppSheet Check-In Integration

## Problem Statement

MARS currently has a parent Google Form, a Google Sheet, an Apps Script project, and an AppSheet staff app, but the handoff between them is incomplete. Parent submissions can land in the Google Forms response tab while the staff-facing `Students` table still needs reliable mapping of the current form fields. The AppSheet app also needs a fast, safe workflow for staff to find eligible students, check them in, verify pickup adults, check them out, and correct mistakes.

Staff need one operational center for event-day work. They must not have to search through raw form responses, retype student information, use a separate parent workflow, or require individual Google accounts. Students with incomplete waivers must be clearly separated from eligible students and must not be checked in accidentally. The system must retain timestamps, staff session names, correction reasons, and event identity so that it can be reused for future events and audited afterward.

## Solution

Use the Google Sheet as the canonical operational data layer and AppSheet as the centralized staff interface. The parent form remains the intake interface, with one submission per child, a required electronic legal-name acknowledgement, pickup contacts, medical information, and a link to the official view-only PDF. An Apps Script mapper will read response headers by name, preserve legacy response columns, normalize the newest form fields, and upsert the matching child into `Students`.

AppSheet will provide a shared-PIN staff entry flow, a required staff session name, a Today dashboard, fast name and preferred-name search, group filters, eligible and Needs Attention sections, check-in and check-out actions, authorized-pickup verification, timestamps, and correction actions. The app will read event configuration from the private `Config` table so the same system can support future events by changing configuration rather than rebuilding the workflow.

## User Stories

1. As a parent or legal guardian, I want to read the official participation agreement before submitting the form, so that I understand what I am acknowledging.
2. As a parent or legal guardian, I want to submit one form for one child, so that each child has a distinct waiver record.
3. As a parent or legal guardian, I want the form to use clear final labels, so that I do not see confusing placeholder choices or internal field names.
4. As a parent or legal guardian, I want to provide the child’s legal name, preferred name, grade, birth date, address, and guardian information, so that staff can identify the child accurately.
5. As a parent or legal guardian, I want to provide emergency contact information, so that staff can respond appropriately if needed.
6. As a parent or legal guardian, I want to provide medical, allergy, dietary, accessibility, and safety information, so that staff can see important needs without asking me to repeat the form.
7. As a parent or legal guardian, I want to provide up to three pickup contacts with names, relationships, and phone numbers, so that staff can verify who may pick up the child.
8. As a parent or legal guardian, I want to give the required electronic acknowledgement by entering my full legal name, so that the submission records my acknowledgement.
9. As a parent or legal guardian, I want media consent handled separately from admission eligibility, so that declining media use does not prevent participation.
10. As a parent or legal guardian, I want the form submission to receive a timestamp, so that the organization can establish when the acknowledgement was received.
11. As an event administrator, I want legacy form-response columns preserved, so that editing the form does not destroy historical response data.
12. As an event administrator, I want new form fields mapped by header name rather than column position, so that future form edits do not silently corrupt student records.
13. As an event administrator, I want a submitted waiver to become complete only when the required acknowledgement is affirmative and the child match is reliable, so that incomplete or ambiguous submissions require review.
14. As an event administrator, I want roster-only values such as StudentID, group, and Active status preserved during form updates, so that intake cannot overwrite operational assignments.
15. As staff, I want to enter one shared PIN, so that staff can access the app without individual Google accounts.
16. As an event administrator, I want to rotate the shared PIN from private configuration, so that the same system can be secured for future events.
17. As staff, I want to enter my name after the PIN, so that every attendance action records who performed it.
18. As staff, I want to land on a Today dashboard, so that I can begin event-day work without navigating through administrative tables.
19. As staff, I want to search by legal or preferred student name, so that I can find a student quickly at check-in.
20. As staff, I want Group A, Group B, and Group C quick filters, so that I can narrow the list when many students arrive together.
21. As staff, I want eligible students shown separately from students needing attention, so that I can process ready students quickly.
22. As staff, I want students with incomplete waivers blocked from check-in, so that no child enters before the required agreement is complete.
23. As staff, I want a student’s group and waiver status visible before check-in, so that I can verify I selected the correct child.
24. As staff, I want Check In to create or update the correct attendance record for the current event date, so that I do not have to type the date manually.
25. As staff, I want check-in time and staff name recorded automatically, so that attendance is auditable.
26. As staff, I want duplicate check-ins prevented for the same child and event date, so that attendance counts remain accurate.
27. As staff, I want to see who is currently checked in, so that I know which students remain at the event.
28. As a parent or guardian, I want to speak with staff at pickup rather than use the staff app myself, so that the staff member controls the release decision.
29. As staff, I want to see the authorized pickup contacts while checking out, so that I can compare the pickup adult with the submitted authorization.
30. As staff, I want to record the pickup adult’s name and relationship, so that the release record is understandable later.
31. As staff, I want to confirm pickup verification before checkout is finalized, so that an unverified adult cannot be recorded accidentally.
32. As staff, I want Check Out to record the current timestamp and my session name automatically, so that release timing and responsibility are documented.
33. As staff, I want to correct an attendance mistake from the app, so that small event-day errors do not require editing raw sheets.
34. As staff, I want every correction to require a reason and timestamp, so that corrections remain accountable.
35. As staff, I want quick links to the schedule, site map, master links, official PDF, and parent form, so that common troubleshooting information is close at hand.
36. As an event administrator, I want the system to show configuration and operational problems clearly, so that staff can resolve common issues without searching through raw tabs.
37. As an event administrator, I want the event date, event ID, location, waiver version, form URL, and PDF URL configurable, so that the system can be reused for future events.
38. As an event administrator, I want the spreadsheet timezone used consistently, so that form, check-in, checkout, and correction timestamps agree.
39. As an event administrator, I want operational tabs visible and backend tabs hidden, so that staff can navigate the sheet without accidentally changing system data.
40. As an event administrator, I want a complete audit trail without exposing student data publicly, so that the GitHub record documents the system while private data remains in Google Workspace.

## Implementation Decisions

- The canonical integration seam is the Google Sheet data contract: `Form Responses 1` supplies intake, `Students` supplies eligibility and identity, `Attendance` supplies event-day state, and `Config` supplies event and workflow settings.
- Apps Script will map current form response headers by exact normalized header names, preferring the newest duplicate header when Google Forms has retained legacy columns.
- The response tab will remain hidden and legacy columns will not be deleted.
- Form intake will update child information and waiver/pickup fields while preserving roster-owned fields such as StudentID, Group, Active, Source, CreatedAt, and operational assignments.
- A reliable child match is required before a waiver can set `WaiverComplete` to `YES`; ambiguous or missing matches go to a review/attention path.
- `WaiverTimestamp` comes from the form response timestamp, and `WaiverVersion` comes from private configuration.
- The current Students schema includes three authorized pickup slots, each with name, relationship, and phone fields.
- The current Attendance schema includes EventDate, StudentID, check-in/check-out fields, pickup verification fields, EventID, CorrectionReason, and CorrectionTimestamp.
- EventDate is derived from the current date in `America/Los_Angeles` for the current event, rather than entered by staff.
- Check-in eligibility is `Active = YES` and `WaiverComplete = YES`. Needs Attention contains incomplete, unmatched, inactive, or otherwise blocked records.
- Attendance uniqueness is enforced by StudentID plus EventID/EventDate, preventing a second active check-in for the same event day.
- The staff workflow uses one shared PIN stored privately in `Config`, followed by a required staff session name. The app must not require individual Google account sign-in for event-day staff.
- The shared PIN must never appear in the public GitHub repository or visible parent-facing links.
- Check-in, checkout, and correction actions write timestamps and staff session names automatically; staff should not type those values.
- Checkout is a staff-controlled workflow. The parent/guardian does not operate the app; staff verify the adult against the authorized pickup slots and record the release.
- Corrections are exposed as an explicit action and require a reason before saving.
- AppSheet views and actions are built on the four canonical tables, with regenerated columns after the latest sheet schema changes.
- The app includes Today, search, group filters, Eligible to Check In, Needs Attention, Currently Checked In, quick links, and troubleshooting/configuration views.
- The parent form description and Master Links table point to the official view-only PDF and public form. The form editor URL remains private.
- Future event reuse is achieved by changing Config values such as EVENT_ID, EVENT_DATES, EVENT_LOCATION, WAIVER_VERSION, and active form/PDF links.
- GitHub stores sanitized documentation and implementation records only; live student data, live PINs, private response links, and private form-editor links stay in Google Workspace.

## Testing Decisions

- Tests will verify observable behavior at the Google Sheet data-contract seam and through the AppSheet user workflow, rather than testing internal implementation details.
- Form mapping tests will use representative response rows containing the current headers, retained legacy headers, missing optional pickup contacts, and affirmative/non-affirmative acknowledgements.
- Mapping tests will verify that the newest duplicate header wins, legacy columns remain untouched, roster-owned fields remain preserved, and timestamps are carried through.
- Eligibility tests will cover complete waiver, incomplete waiver, ambiguous match, inactive student, and missing student cases.
- Attendance tests will cover successful check-in, duplicate check-in prevention, wrong-event-date prevention, automatic timestamp/staff attribution, and visibility in Currently Checked In.
- Checkout tests will cover authorized pickup, unverified pickup, required pickup fields, automatic timestamp/staff attribution, and removal from Currently Checked In.
- Correction tests will verify that a correction cannot save without a reason and that the correction timestamp and staff session are recorded.
- Future-event tests will change Config event dates and event ID, then verify that attendance writes use the new configuration without changing the underlying schema.
- Navigation tests will verify that staff can reach the schedule, site map, master links, official PDF, and parent form from the app.
- The event-day acceptance test will use a small non-production test roster and at least two staff devices to verify the complete flow before live use.
- The production readiness check will confirm that backend/admin sheets remain hidden, private Config values are not exposed, and no public GitHub artifact contains student data or secrets.

## Out of Scope

- Rewriting or legally reviewing the participation agreement text.
- Requiring parents to use AppSheet for check-in or checkout.
- Parent accounts, parent PINs, payments, merchandise, or registration billing.
- Automatic photo/video consent decisions beyond storing the form response.
- A public-facing student or parent portal.
- Replacing Google Forms, Google Sheets, Apps Script, or AppSheet with a custom web/mobile application.
- Deleting old response columns or destroying historical form data.
- Publishing private student records, private links, or the staff PIN to GitHub.

## Further Notes

- The live Google Sheet already contains the expanded Students and Attendance headers, private integration configuration, and visible Master Links entries.
- The remaining implementation work is the Apps Script header-based mapper deployment and the AppSheet table regeneration, security/session flow, views, actions, and acceptance test.
- Before implementation begins, confirm that the single canonical seam—Google Sheet data contract feeding AppSheet—is the expected architecture. If accepted, split this spec into implementation tickets and work blockers first.
