# PhoneOps Remote Phone Link

The **Remote Phone Link** panel creates a short-lived 15-minute pairing URL for a selected PhoneOps slot. The link is intended for a phone-side companion bridge to claim the slot and report its device identity. It is not a public unauthenticated control endpoint.

The current link service provides the pairing-token lifecycle and connection status. A production companion should exchange the token over HTTPS, bind the phone to the selected slot, rotate credentials after pairing, and maintain an authenticated WebSocket or WebRTC session.

## Screen mirroring boundary

The Muse Gadget SDK is a device-command bridge for Linux and ESP32 gadgets. It does not by itself provide Android or iPhone screen mirroring. For Android, the companion can use an approved ADB/scrcpy pipeline or a signed screen-capture service. For iPhone, the companion needs a ReplayKit-based capture extension and a WebRTC transport. The captured frames should be sent to the PhoneOps browser panel through an authenticated media channel.

PhoneOps deliberately shows this boundary in the UI rather than claiming that a pairing link alone mirrors a screen. The safe next implementation is:

1. Create a pairing link from PhoneOps.
2. Open it in the phone-side companion.
3. Exchange the one-time token over HTTPS.
4. Register the real device metadata.
5. Establish an authenticated WebRTC media session for the screen.
6. Route only explicitly approved device commands through the companion.

The prototype API endpoints are `POST /api/remote/link`, `POST /api/remote/connect`, and `GET /api/remote/status`. The generated tokens expire after 15 minutes.
