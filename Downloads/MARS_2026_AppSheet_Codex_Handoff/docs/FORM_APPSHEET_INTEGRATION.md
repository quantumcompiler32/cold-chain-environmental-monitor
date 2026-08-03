# Form and AppSheet Integration

This document describes the production mapping for the MARS parent form and staff check-in app. It intentionally contains no student records, staff secrets, or private editor URLs.

## Source of truth

- Parent form and official agreement PDF: use the links recorded in the private Google Sheet `Config` tab.
- Form response tab: `Form Responses 1` (hidden; do not delete legacy columns).
- AppSheet-facing tables: `Students`, `Attendance`, `StaffUsers`, and `Config`.

## Form response to Students mapping

Use the newest visible form headers when duplicate legacy headers exist. Do not map by column number because Google Forms preserves old response columns after edits.

| Form header | Students column |
|---|---|
| Child’s Full Legal Name | StudentName |
| Child’s Preferred Name | PreferredName |
| Child’s Grade | Grade |
| Child’s Date of Birth | DateOfBirth |
| Home Address | HomeAddress |
| City, State, and ZIP Code | CityStateZIP |
| Parent or Legal Guardian Full Name | GuardianName |
| Relationship to Child | GuardianRelationship |
| Parent or Legal Guardian Email | GuardianEmail |
| Parent or Legal Guardian Phone Number | GuardianPhone |
| Emergency Contact Full Name / Relationship / Phone Number | EmergencyContactName / EmergencyContactRelationship / EmergencyContactPhone |
| Medical Information, Allergies, Dietary Restrictions, or Accessibility Needs | MedicalSummary |
| Medical or Safety Information on File? | MedicalOnFile |
| Pickup Contact 1 Name / Relationship / Phone Number | AuthorizedPickup1Name / AuthorizedPickup1Relationship / AuthorizedPickup1Phone |
| Pickup Contact 2 Name / Relationship / Phone Number | AuthorizedPickup2Name / AuthorizedPickup2Relationship / AuthorizedPickup2Phone |
| Pickup Contact 3 Name / Relationship / Phone Number | AuthorizedPickup3Name / AuthorizedPickup3Relationship / AuthorizedPickup3Phone |
| Required Electronic Acknowledgment | WaiverComplete = YES only when the required acknowledgement is affirmative |
| Parent or Legal Guardian Full Legal Name for Electronic Acknowledgment | Waiver signer/audit value |
| Timestamp | WaiverTimestamp |
| Optional Photo and Video Consent | Store in waiver/audit data; media consent is separate from admission eligibility |

Preserve StudentID, Group, Active, Source, and other operational roster values. Set WaiverVersion from the private `Config` tab. A submitted form must not make a student eligible unless the acknowledgement is complete and the response is matched to the correct child.

## Attendance rules

- EventDate is the current date in the spreadsheet timezone, not a date typed by staff.
- Check-in is allowed only when Active = YES and WaiverComplete = YES.
- Incomplete waiver records appear in a separate Needs Attention view and cannot be checked in.
- Prevent a second check-in for the same StudentID and EventDate.
- Check-out requires staff to verify the pickup adult against authorized pickup contacts, then records the adult, relationship, verification, checkout time, and staff name.
- Staff corrections require CorrectionReason and CorrectionTimestamp.
- Every check-in, check-out, and correction keeps a timestamp and staff session name.

## AppSheet build requirements

1. Refresh/regenerate all four table structures so the pickup and attendance audit columns appear.
2. Use the shared PIN flow in private `Config`; do not require staff Google account sign-in. Require a staff name after PIN entry and keep it in the session.
3. Create a Today dashboard with search by child/preferred name, group quick filters, Eligible to Check In, Needs Attention, Currently Checked In, and quick links to the schedule, site map, master links, PDF, and parent form.
4. Show Check In only for eligible students and Check Out only for currently checked-in students. Confirm checkout after showing authorized pickup contacts.
5. Make corrections a visible action requiring a reason; do not allow silent timestamp or staff-field edits.
6. Add an admin-only configuration view for rotating the shared PIN and updating future event configuration.

The system is reusable for future events by changing private Config values such as EVENT_ID, EVENT_DATES, EVENT_LOCATION, WAIVER_VERSION, and the active form/PDF links. Never commit Config secrets or live response data to this repository.
