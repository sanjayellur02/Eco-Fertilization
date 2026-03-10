/* ===============================
   LOCATION TOGGLE (MANUAL / AUTO)
================================ */
function toggleManual(showManual) {
    const manual = document.getElementById("manualLocation");
    const autoLoc = document.getElementById("autoLocation");

    if (manual && autoLoc) {
        manual.style.display = showManual ? "block" : "none";
        autoLoc.style.display = showManual ? "none" : "block";
    }
}

/* ===============================
   GET CURRENT LOCATION (GPS)
================================ */
function getLocation() {
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            document.getElementById("latitude").value =
                position.coords.latitude;
            document.getElementById("longitude").value =
                position.coords.longitude;

            document.getElementById("locationStatus").innerText =
                "Location captured successfully ✔";
        },
        () => {
            alert("Location access denied. Please enter manually.");
        }
    );
}
