from deepface import DeepFace
import cv2
import os
import time

# Path to your known face database
DB_PATH = "C:/database"

# Initialize webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("❌ Could not access webcam!")

print("✅ Real-time face recognition + emotion analysis started.")
print("Press 'q' to quit.\n")

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Frame capture failed, retrying...")
        continue

    try:
        # Step 1: Find the identity in your face database
        results = DeepFace.find(
            img_path=frame,
            db_path=DB_PATH,
            enforce_detection=False,
            detector_backend="opencv"
        )

        # Step 2: Run emotion analysis on the current frame
        analysis = DeepFace.analyze(
            img_path=frame,
            actions=['emotion'],
            enforce_detection=False,
            detector_backend="opencv"
        )

        # Step 3: Print recognition + emotion in terminal
        print("\n--------------------------------------------")
        if len(results) > 0 and not results[0].empty:
            identity = results[0].iloc[0]['identity']
            confidence = 100 - results[0].iloc[0]['distance'] * 100
            print(f"🧠 Identity: {identity}")
            print(f"   Confidence: {confidence:.2f}%")
        else:
            print("❓ No match found in database")

        print(f"   Emotion: {analysis[0]['dominant_emotion']}")
        print(f"   Emotion scores: {analysis[0]['emotion']}")
        print("--------------------------------------------")

    except Exception as e:
        print("⚠️ Analysis error:", e)

    # Display the camera feed (optional — you can comment this out)
    cv2.imshow("DeepFace Stream (Press 'q' to quit)", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # Small pause to avoid CPU overload
    time.sleep(0.2)

cap.release()
cv2.destroyAllWindows()
print("🛑 Stream ended.")
