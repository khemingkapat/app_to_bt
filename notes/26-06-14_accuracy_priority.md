# 🎯 Project Core Principle: Absolute Accuracy & Zero-Error Tolerance

## 1. Requirement Definition
During design alignment, we established that the absolute priority of this project is **data correctness**. Because this system manages insurance underwriting and legal contracts:
* We operate under a **zero error tolerance policy**.
* No data truncation, incorrect mappings, or miscalculations can reach the final outputs.
* A submission queue system remains a future consideration; focus is strictly on data capture, verification, and output fidelity.

---

## 2. Safety Shields & Integrity Mechanisms
To enforce zero-error tolerance, the application implements the following safeguards:

### A. Real-Time Health gate (Screen 1)
* Prevents high-risk applications from propagating. Chronic conditions block the workflow immediately.

### B. ID Assisted OCR Intake Verification (Screen 3)
* Simulates OCR scanning to pre-fill Name, DOB, and Address.
* Pre-filled fields are highlighted in yellow and marked with a **`⚠️ Review pre-filled info`** warning badge.
* This mandates a **Human-in-the-Loop (HITL)** check, ensuring the applicant verifies OCR results against their physical ID before submission.

### C. Robust Date Splitting Parser
* In the inverter, the date string (`DD/MM/YYYY`) is automatically parsed and mapped to the split fields on the PDF (Day, Month, Year) by matching the page and field labels.
* Handles multiple formats (hyphens, slashes) dynamically with fallback safety.

---

## 3. Quality Assurance (Pre-commit Validation)
* **Pricing Unit Tests (`test_pricing.py`):** Asserts standard pricing brackets, deductibles, spouse premiums, and child premiums across plan tiers.
* **PDF Field Mapping Tests (`test_inverter.py`):** Verifies correct mapping from data keys to AcroForm field tags.
* **E-Form End-to-End Tests (`test_app.py`):** UI automation validating E-Form navigation steps and success states.
