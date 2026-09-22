# Submission working facts

## OneAquaHealth — prospective Track 3

Streamproof supports urban freshwater citizen observations through photograph quality checks, repeat-view consistency and a human-reviewed evidence packet. Its core contribution is choosing the next useful observation from actual vision output while preserving uncertainty. The working prototype is original work begun September 21, 2026.

Registration eligibility is not assumed: the published rules said registration closed August 31 despite an active Join button. Organizer clarification remains outside this repository. Do not present the project as entered until the portal or organizer verifies submission acceptance.

## OpenCV Spatial AI Hackathon 2026 — prospective agentic vision entry

The installed official PyPI distribution is `opencv-python-headless==5.0.0.93`, and `cv2.__version__` actually reports `5.0.0`. OpenCV performs all quality measurement, features, registration, masking and appearance comparison. The inspectable agentic loop is deterministic, not LLM-based: measured image evidence changes the requested next observation. Human interpretation is retained.

Meaningful AWS execution is required but is **not yet verified**. See the deployment guide. Proposal/admission ambiguity requires organizer clarification before claiming eligibility. The root campaign owns outreach, publishing, deployment and submission; this file records technical facts, not completion of those actions.

## Suggested live demonstration, under five minutes

- The problem: a citizen's photograph raises a question but an expert needs better, comparable evidence.
- Process the historical CC0 River Ver photograph, confirm the selected region and show the baseline request.
- Run the explicitly labeled synthetic pair. Show the source fingerprint, bank alignment, measured appearance difference and close/upstream-photo request.
- Show the lighting-shift and blur cases changing the next action rather than generating a confident environmental diagnosis.
- Record a human assessment and export the verifiable JSON/GeoJSON evidence.
- Explain the actual architecture, versions, AWS runtime if deployed, test results, and the lack of field validation.

The video must distinguish real UI execution from prerecorded or synthetic scene content. The image pair is synthetic; the processing and outputs are actual. Public photographs are historical demonstrations. No customer, scientific validation or prize claim is available.

## AI and originality disclosure

AI assistance was used for research, original implementation, UI writing and test development. The system itself uses inspectable OpenCV methods and a deterministic policy, without an LLM inference dependency. Third-party images are attributed CC0 materials; programmed controls and original code are MIT. This is not an earlier submitted hackathon project. Any later reuse or cross-entry should be disclosed and checked against the respective organizer's final rules.
