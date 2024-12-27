// Language Switcher Logic
function changeLanguage() {
    const selectedLang = document.getElementById('languageSelect').value;
    const body = document.body;
    const translations = {
        en: {
            languageSelectLabel: "Select Language:",
            carNumberLabel: "Car Number:",
            carOwnershipLabel: "Car Ownership:",
            carCodeLabel: "Car Code:",
            inspectorIdLabel: "Administrative number:",
            pullAreaLabel: "Pull Area:",
            dischargeAreaLabel: "Discharge Area:",
            notesLabel: "Notes:",
            locationLabel: "Location:",
            submitButton: "Submit",
            formTitle: "Rain Service",
            photoLabel: "Photo:",
            getLocationButton: "Get Location"
        },
        ar: {
            languageSelectLabel: "تغير اللغة:",
            carNumberLabel: "رقم المركبة:",
            carOwnershipLabel: "ملكية السيارة:",
            carCodeLabel: "كود المركبة:",
            inspectorIdLabel: "الرقم الإداري:",
            pullAreaLabel: "منطقة السحب:",
            dischargeAreaLabel: "منطقة التفريغ:",
            notesLabel: "الملاحظات:",
            locationLabel: "الموقع:",
            submitButton: "إرسال",
            formTitle: "خدمة سحب الأمطار",
            photoLabel: "صورة:",
            getLocationButton: "الحصول على الموقع"
        }
    };

    if (selectedLang === 'ar') {
        body.classList.remove('ltr');
        body.classList.add('rtl');
    } else {
        body.classList.remove('rtl');
        body.classList.add('ltr');
    }

    const langContent = translations[selectedLang];
    for (const key in langContent) {
        const element = document.getElementById(key);
        if (element) {
            element.innerText = langContent[key];
        }
    }
}

// Get User Location
function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition((position) => {
            const coords = `Lat: ${position.coords.latitude}, Lng: ${position.coords.longitude}`;
            document.getElementById('location').value = coords;
        });
    } else {
        alert("Geolocation is not supported by this browser.");
    }
}

// Handle Form Submission
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById("dataEntryForm");
    if (form) {
        form.onsubmit = async function(e) {
            e.preventDefault();
            
            // Validate required fields
            const requiredFields = ['carNumber', 'carOwnership', 'carCode', 'inspectorId', 'pullArea', 'dischargeArea'];
            for (const field of requiredFields) {
                const input = document.getElementById(field);
                if (!input.value.trim()) {
                    alert(`Please fill in ${field}`);
                    return;
                }
            }

            // Create FormData and append all form fields
            const formData = new FormData();
            formData.append('carNumber', document.getElementById('carNumber').value.trim());
            formData.append('carOwnership', document.getElementById('carOwnership').value);
            formData.append('carType', document.getElementById('carType').value.trim());
            formData.append('carCode', document.getElementById('carCode').value.trim());
            formData.append('inspectorId', document.getElementById('inspectorId').value.trim());
            formData.append('pullArea', document.getElementById('pullArea').value.trim());
            formData.append('dischargeArea', document.getElementById('dischargeArea').value.trim());
            formData.append('notes', document.getElementById('notes').value.trim());
            formData.append('location', document.getElementById('location').value.trim());

            // Handle photo file
            const photoInput = document.getElementById('photo');
            if (photoInput.files.length > 0) {
                formData.append('photo', photoInput.files[0]);
            }

            try {
                const response = await fetch('/submit', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Submission failed');
                }

                const data = await response.json();
                if (data.reference_number) {
                    document.getElementById("thankYouMessage").style.display = "block";
                    document.getElementById("refNumber").innerText = data.reference_number;

                    const message = `Your reference number: ${data.reference_number}`;
                    document.getElementById("whatsappLink").href = `https://wa.me/?text=${encodeURIComponent(message)}`;
                    document.getElementById("telegramLink").href = `https://t.me/share/url?url=${encodeURIComponent(message)}`;
                    
                    // Clear form
                    form.reset();
                    document.getElementById('location').value = '';
                }
            } catch (error) {
                console.error('Submission error:', error);
                alert('Error submitting form: ' + error.message);
            }
        };
    }

    // Initialize language
    changeLanguage();
});

function openCamera() {
    const photoInput = document.getElementById('photo');
    photoInput.setAttribute('capture', 'environment');
    photoInput.click();
}

function toggleCarFields() {
    const ownership = document.getElementById('carOwnership').value;
    const carType = document.getElementById('carType');
    const carCode = document.getElementById('carCode');
    
    if (ownership === 'Government') {
        carType.value = 'Government Vehicle';
        carCode.value = 'GOV';
        carType.disabled = true;
        carCode.disabled = true;
    } else {
        carType.value = '';
        carCode.value = '';
        carType.disabled = false;
        carCode.disabled = false;
    }
}