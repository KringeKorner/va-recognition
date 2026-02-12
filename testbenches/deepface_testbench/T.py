from deepface import DeepFace
import cv2
import matplotlib.pyplot as plt

# Path to your image
img_path = "img1.png"

# Load image with OpenCV (ensures it exists and is readable)
img = cv2.imread(img_path)
if img is None:
    raise FileNotFoundError(f"❌ Image not found at path: {img_path}")

# Convert BGR (OpenCV) → RGB (DeepFace expects RGB)
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# Show image to confirm it’s being read properly
plt.imshow(img_rgb)
plt.axis("off")
plt.title("Analyzed Image")
plt.show()

# Run DeepFace analysis
print("🔍 Running DeepFace analysis...")
results = DeepFace.analyze(
    img_path=img_rgb,  # you can also pass the numpy array
    actions=['age', 'gender', 'race', 'emotion'],
    enforce_detection=False  # prevents crash if face not detected perfectly
)

# Display structured results
print("\n✅ DeepFace Analysis Results:")
for face in results:
    print(f"\nFace #{face['region']}:")
    print(f"  Age: {face['age']}")
    print(f"  Gender: {face['dominant_gender']}")
    print(f"  Emotion: {face['dominant_emotion']}")
    print(f"  Race: {face['dominant_race']}")

# Or simply print full JSON output if you prefer
# print(results)
