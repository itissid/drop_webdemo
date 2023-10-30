function showAlert(message) {
    var alertElement = document.getElementById('alert');
    alertElement.innerHTML = '<strong>Warning!</strong> ' + message;
    alertElement.classList.add('show');
    alertElement.style.display = 'block';
}

function hideAlert() {
    var alertElement = document.getElementById('alert');
    alertElement.classList.remove('show');
    alertElement.style.display = 'none';
}

function displayError(message) {
    const errorElement = document.getElementById('error');
    errorElement.textContent = message;
    errorElement.classList.remove('hidden');
}

async function areYouHere(lat, lng) {
    try {
        const response = await fetch(`/presence/are_you_really_here/?lat=${lat}&long=${lng}`);

        if (!response.ok) {
            // The server responded with an error status
            const errorData = await response.json();
            showAlert(errorData.detail);
            return;
        }
        console.log("You are here.")
        window.location.href = `/presence/here/?lat=${lat}&long=${lng}`

    } catch (error) {
        displayError(error.message);
    }
}



/** Be here now functions **/

document.addEventListener('DOMContentLoaded', function () {
    var toggleButton = document.getElementById('toggleButton');
    var overlay; // Holds the overlay element

    // Function to create the overlay element
    function createOverlay() {
        overlay = document.createElement('div');
        overlay.className = 'my_bg_image'; // This class is defined in the CSS and contains the styles
        document.body.appendChild(overlay);
    }

    // Event listener for the toggle button
    toggleButton.addEventListener('change', function () {
        if (toggleButton.checked) {
            // If the switch is 'on', create and display the overlay
            createOverlay();
            var sound = document.getElementById("pitter-patter");
            sound.play()
        } else {
            // If the switch is 'off', remove the overlay from the DOM
            if (overlay) {
                document.body.removeChild(overlay);
                var sound = document.getElementById("pitter-patter");
                sound.pause()
                sound.currentTime = 0;
            }
        }
    });
    var offset = 5
    var sound = document.getElementById("pitter-patter");
    sound.addEventListener('ended', function() {
        this.currentTime = offset;
        this.play();
    });
});


