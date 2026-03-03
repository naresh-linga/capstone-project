🚦 AccidentAI Pro: An Intelligent Vision-Based Road Accident Detection and Analytics System
📄 Abstract

Road traffic accidents remain a major cause of mortality and infrastructure damage worldwide. This project presents AccidentAI Pro, an intelligent computer vision-based accident detection and analytics framework designed to enable real-time monitoring, incident logging, and risk assessment.

The system integrates YOLO-based object detection, OpenCV-based video processing, and a Flask backend with an interactive analytics dashboard. It provides safety score computation, trend analysis, and structured reporting to support data-driven decision-making in smart transportation systems.

🔎 Keywords

Computer Vision, YOLOv8, Road Safety, Real-Time Detection, Flask, Data Analytics, Vision Zero, Intelligent Transportation Systems

1️⃣ Introduction

AccidentAI Pro is developed under the Vision Zero initiative, aiming to minimize road accidents using AI-driven monitoring systems.

The system processes live webcam streams or uploaded images to detect potential accident events. Detected incidents are logged into a database and visualized through an advanced analytics dashboard.

2️⃣ System Architecture

The proposed architecture consists of five primary modules:

Data Acquisition Layer

Webcam stream / Image upload

Detection Layer

YOLOv8 model for accident detection

Processing Layer

OpenCV frame processing

Backend Layer

Flask REST API

Database integration (MySQL)

Visualization Layer

HTML/CSS Dashboard

Chart.js Analytics

3️⃣ Methodology
🔹 Step 1: Image/Video Input

Video frames are captured in real time using OpenCV.

🔹 Step 2: Object Detection

YOLOv8 model processes frames and detects accident-related events.

🔹 Step 3: Confidence Evaluation

Each detection is assigned a confidence score.

🔹 Step 4: Data Logging

Incident details (timestamp, label, confidence, source) are stored in MySQL database.

🔹 Step 5: Analytics Generation

Dashboard visualizes:

Detection frequency

Safety score

Hourly density heatmap

Incident logs

CSV export

4️⃣ Features

✅ Real-time accident detection

✅ Upload-based detection support

✅ Interactive analytics dashboard

✅ Safety score computation

✅ Hourly risk density analysis

✅ CSV report export

✅ Modern enterprise UI

5️⃣ Technology Stack
Layer	Technology
Programming Language	Python 3.9+
Detection Model	YOLOv8
Computer Vision	OpenCV
Backend Framework	Flask
Database	MySQL
Frontend	HTML5, CSS3
Visualization	Chart.js
UI Icons	Font Awesome
6️⃣ Analytics Module Description
📊 Detection Frequency Analysis

Line graph representing accident trends over time.

🛡 Safety Score Estimation

Risk percentage calculated as:

Safety Score = 100 − (Accidents / Total Scans × 100)

Color-coded gauge:

Green → Safe

Orange → Moderate Risk

Red → High Risk

📈 Hourly Density Heatmap

Visual representation of peak accident hours.

📁 Incident Log Table

Structured display including:

Timestamp

Detection ID

Incident Type

Confidence Score

Source (Webcam / Upload)

7️⃣ Project Structure
