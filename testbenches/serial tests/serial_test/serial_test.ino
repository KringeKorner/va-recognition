int source = 0;
int detectedMood = 0;
int sourceLeds[2] = {2, 7};
int moodLeds[4] = {3, 4, 5, 6};
int i = 0;
unsigned long lastReadyTime = 0;

void setup() {
  Serial.begin(115200);
  for(i=0;i<2;i++){
    pinMode(sourceLeds[i], OUTPUT);  
  }
  for(i=0;i<4;i++){
    pinMode(moodLeds[i], OUTPUT);  
  }
  for(i=2;i<8;i++){
    digitalWrite(i, HIGH); 
    delay(500);
    digitalWrite(i, LOW); 
  }
}

void loop() {
  unsigned long now = millis();
  if(now - lastReadyTime > 50) {
    Serial.println("READY");
    lastReadyTime = now;
  }
  if(Serial.available() >= 2) {
    source = Serial.read();
    detectedMood = Serial.read();
    Serial.println("Received: " + String(source) + ", " + String(detectedMood));
    processData(source, detectedMood);
  }
}

void processData(int source, int mood){
  for(int i = 0; i < 2; i++){
    int bit = (source >> i) & 1;
    digitalWrite(sourceLeds[i], bit);
  }
  for(int i = 0; i < 4; i++){
    int bit = (mood >> i) & 1;
    digitalWrite(moodLeds[i], bit);
  }
  delay(1000);
  for(int i=0; i<2; i++) digitalWrite(sourceLeds[i], LOW);
  for(int i=0; i<4; i++) digitalWrite(moodLeds[i], LOW);
  delay(1000);
}
