# 🌿 Plant Disease Recognition System

A deep learning–based web application for detecting and classifying plant diseases from leaf images.

---

## 📊 Dataset

This project uses the **PlantVillage dataset** provided by TensorFlow Datasets.

🔗 Dataset Link: https://www.tensorflow.org/datasets/catalog/plant_village

The dataset contains over **54,000 images** of healthy and diseased plant leaves across **38 classes**, covering multiple plant species and disease types.

---

## 📦 Model Setup

To run this project, you must download the pre-trained model and place it in the correct directory.

---

## 📥 Download Pre-trained Model

Due to GitHub file size limitations, the trained model is not included in this repository.
You need to download it manually from Google Drive.

🔗 **Model Download Link:**
https://drive.google.com/file/d/1jRrWxMdkQKnl96DYnskRaI-qvKfRixoz/view?usp=sharing

---

### 📌 Setup Instructions

1. Download the model file from the link above
2. Extract it if it is in `.zip` format
3. Move the downloaded `.keras` file into the following directory:

```
Plant-Disease-Recognition-Model-Using-Deep-Learning/models/
```

4. Make sure the file name remains unchanged
5. Now you are ready to run the project

⚠️ **Important:** The application will not work without the model file.

---

## 🎥 Reference Video

For better understanding of the implementation and workflow, you can watch this video:

▶️ https://www.youtube.com/watch?v=0BL42NXimF4&t=2002s

---

## 🚀 How to Run the Project

Install dependencies:

```
pip install -r requirements.txt
```

Run the application:

```
python app.py
```

Then open your browser and go to:

```
http://127.0.0.1:5000/
```

---

## 📌 Features

* Upload plant leaf images
* Detect and classify plant diseases
* Fast and accurate predictions using deep learning
* Simple and user-friendly web interface

---

## 🧠 Technology Used

* Python
* TensorFlow / Keras
* Flask
* HTML, CSS, JavaScript

---

## 📁 Project Structure

```
Plant-Disease/
│
├── models/
├── static/
├── templates/
├── uploadimages/
├── app.py
├── requirements.txt
└── README.md
```

---

## 📌 Note

* Ensure the model file is placed correctly inside the `models/` folder
* Internet is not required after setup
* This project is for educational and research purposes

---
