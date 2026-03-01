import cv2

cap = cv2.VideoCapture(0)
print("Camera opened:", cap.isOpened())

while True:
    ret, frame = cap.read()
    print("Frame read:", ret)
    if not ret:
        print("Cannot read frame - trying index 1")
        break
    cv2.imshow("Test", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()