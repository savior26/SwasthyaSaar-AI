// ============================================================
// SWASTHYASAAR AUTHENTICATION
// ============================================================


// ============================================================
// SECTION SWITCHING
// ============================================================

function showRegister() {

    document
        .getElementById("login-section")
        .classList.remove("active");

    document
        .getElementById("register-section")
        .classList.add("active");

    clearMessages();
}


function showLogin() {

    document
        .getElementById("register-section")
        .classList.remove("active");

    document
        .getElementById("login-section")
        .classList.add("active");

    clearMessages();
}


// ============================================================
// PASSWORD VISIBILITY
// ============================================================

function togglePassword(inputId, button) {

    const input = document.getElementById(inputId);

    if (input.type === "password") {

        input.type = "text";

        button.textContent = "Hide";

    } else {

        input.type = "password";

        button.textContent = "Show";
    }
}


// ============================================================
// MESSAGE HELPERS
// ============================================================

function showError(elementId, message) {

    const element = document.getElementById(elementId);

    element.textContent = message;

    element.style.display = "block";
}


function showSuccess(elementId, message) {

    const element = document.getElementById(elementId);

    element.textContent = message;

    element.style.display = "block";
}


function clearMessages() {

    const messages = document.querySelectorAll(
        ".form-message"
    );

    messages.forEach(message => {

        message.textContent = "";

        message.style.display = "none";

    });
}


// ============================================================
// BUTTON LOADING
// ============================================================

function setLoading(buttonId, loading) {

    const button = document.getElementById(buttonId);

    if (loading) {

        button.classList.add("loading");

        button.disabled = true;

    } else {

        button.classList.remove("loading");

        button.disabled = false;
    }
}


// ============================================================
// LOGIN
// ============================================================

document
    .getElementById("login-form")
    .addEventListener("submit", async function(event) {

        event.preventDefault();

        clearMessages();

        const email =
            document
                .getElementById("login-email")
                .value
                .trim();

        const password =
            document
                .getElementById("login-password")
                .value;


        if (!email || !password) {

            showError(
                "login-error",
                "Please enter your email and password."
            );

            return;
        }


        setLoading("login-button", true);


        try {

            /*
             * IMPORTANT:
             *
             * OAuth2PasswordRequestForm expects:
             *
             * application/x-www-form-urlencoded
             *
             * username = email
             * password = password
             */

            const formData = new URLSearchParams();

            formData.append(
                "username",
                email
            );

            formData.append(
                "password",
                password
            );


            const response = await fetch(
                "/auth/login",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/x-www-form-urlencoded"
                    },

                    body: formData
                }
            );


            const data = await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Invalid email or password."
                );
            }


            // =========================================
            // SAVE JWT
            // =========================================

            localStorage.setItem(
                "access_token",
                data.access_token
            );


            localStorage.setItem(
                "token_type",
                data.token_type || "bearer"
            );


            // =========================================
            // REDIRECT
            // =========================================

            window.location.href = "/";


        } catch (error) {

            showError(
                "login-error",
                error.message
            );

        } finally {

            setLoading(
                "login-button",
                false
            );
        }

    });


// ============================================================
// REGISTER
// ============================================================

document
    .getElementById("register-form")
    .addEventListener("submit", async function(event) {

        event.preventDefault();

        clearMessages();


        const name =
            document
                .getElementById("register-name")
                .value
                .trim();


        const email =
            document
                .getElementById("register-email")
                .value
                .trim();


        const gender =
            document
                .getElementById("register-gender")
                .value;


        const yearValue =
            document
                .getElementById("register-year")
                .value;


        const phone =
            document
                .getElementById("register-phone")
                .value
                .trim();


        const bloodGroup =
            document
                .getElementById("register-blood")
                .value;


        const medicalCondition =
            document
                .getElementById("register-condition")
                .value
                .trim();


        const allergy =
            document
                .getElementById("register-allergy")
                .value
                .trim();


        const password =
            document
                .getElementById("register-password")
                .value;


        const confirmPassword =
            document
                .getElementById("register-confirm")
                .value;


        // =========================================
        // VALIDATION
        // =========================================

        if (!name || !email || !password) {

            showError(
                "register-error",
                "Please fill in all required fields."
            );

            return;
        }


        if (password.length < 6) {

            showError(
                "register-error",
                "Password must contain at least 6 characters."
            );

            return;
        }


        if (password !== confirmPassword) {

            showError(
                "register-error",
                "Passwords do not match."
            );

            return;
        }


        setLoading(
            "register-button",
            true
        );


        // =========================================
        // BUILD USERCREATE JSON
        // =========================================

        const payload = {

            name: name,

            email: email,

            password: password,

            gender: gender || null,

            year_of_birth:
                yearValue
                    ? Number(yearValue)
                    : null,

            medical_condition:
                medicalCondition || null,

            allergy:
                allergy || null,

            blood_group:
                bloodGroup || null,

            phone_number:
                phone || null
        };


        try {

            const response = await fetch(
                "/auth/register_user",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify(payload)
                }
            );


            const data = await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Unable to create account."
                );
            }


            // =========================================
            // SUCCESS
            // =========================================

            showSuccess(
                "register-success",
                "Account created successfully. You can now sign in."
            );


            document
                .getElementById("register-form")
                .reset();


            setTimeout(() => {

                showLogin();

                document
                    .getElementById("login-email")
                    .value = email;

            }, 1200);


        } catch (error) {

            showError(
                "register-error",
                error.message
            );

        } finally {

            setLoading(
                "register-button",
                false
            );
        }

    });


// ============================================================
// CHECK EXISTING TOKEN
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        /*
         * If the user is already logged in,
         * don't force them to login again.
         */

        const token =
            localStorage.getItem(
                "access_token"
            );

        /*
         * You can enable this redirect
         * if /auth.html should never be
         * visible to authenticated users.
         */

        // if (token) {
        //     window.location.href = "/";
        // }

    }
);