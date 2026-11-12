## ADDED Requirements

### Requirement: Multipart operations send their form
Operations whose request body is `multipart/form-data` SHALL send every set form field and file
as a multipart body with the matching `Content-Type` boundary; other operations SHALL keep sending
JSON.

#### Scenario: Document upload
- **WHEN** `UploadCrossBorderInvoice` is called with a context, merchant account, and PDF file
- **THEN** the server receives a multipart form with both fields and the file under its base name
