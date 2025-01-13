This is a Smart Library Assistant webpage, allowing users to interact with various features related to book detection and summary processing using Microsoft Azure AI services.
Features:
Upload Book Cover Image: The user can upload an image of a book cover, and the system detects the book title using Optical Character Recognition (OCR) via Azure.
Fetch Book Summary: After the title is detected, the system fetches the book summary from a CSV file containing book data.
Translate Summary: The user can select a language to translate the fetched summary into. This is done using Azure's Text Translation API.
Narrate Translated Summary: After the summary is translated, the user can click a button to hear the translation using Azure's Text-to-Speech API.
