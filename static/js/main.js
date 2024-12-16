
// Language Switcher Logic
function switchLanguage() {
    const selectedLang = document.getElementById('languageSelect').value;
    const body = document.body;

    if (selectedLang === 'ar') {
        body.classList.remove('ltr');
        body.classList.add('rtl');
    } else {
        body.classList.remove('rtl');
        body.classList.add('ltr');
    }

    // Update Translations
    const translations = {
        en: {
            languageSelectLabel: "Select Language:",
            carNumberLabel: "Car Number:",
            carTypeLabel: "Car Type:",
            carCodeLabel: "Car Code:",
            inspectorIdLabel: "Inspector ID:",
            pullAreaLabel: "Pull Area:",
            dischargeAreaLabel: "Discharge Area:",
            notesLabel: "Notes:",
            locationLabel: "Location:",
            submitButton: "Submit",
            formTitle: "Rain Service",
            photoLabel: "Photo:"
        },
        ar: {
            languageSelectLabel: "تغير اللغة:",
            carNumberLabel: "رقم المركبة:",
            carTypeLabel: "نوع السيارة:",
            carCodeLabel: "كود المركبة:",
            inspectorIdLabel: "رقم المفتش:",
            pullAreaLabel: "منطقة السحب:",
            dischargeAreaLabel: "منطقة التفريغ:",
            notesLabel: "الملاحظات:",
            locationLabel: "الموقع:",
            submitButton: "إرسال",
            formTitle: "خدمة سحب الأمطار",
            photoLabel: "صورة:"
        }
    };

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
            const formData = new FormData(this);
            try {
                const response = await fetch("/submit", {
                    method: "POST",
                    body: formData
                });

                const data = await response.json();
                if (!response.ok) {
                    alert('Error submitting form: ' + data.error);
                    return;
                }
                if (data.reference_number) {
                    document.getElementById("thankYouMessage").style.display = "block";
                    document.getElementById("refNumber").innerText = data.reference_number;

                    const message = `Your reference number: ${data.reference_number}`;
                    document.getElementById("whatsappLink").href = `https://wa.me/?text=${encodeURIComponent(message)}`;
                    document.getElementById("telegramLink").href = `https://t.me/share/url?url=${encodeURIComponent(message)}`;
                }
            } catch (error) {
                alert('Error submitting form: ' + error);
            }
        };
    }

    // Set default language
    switchLanguage();
});
