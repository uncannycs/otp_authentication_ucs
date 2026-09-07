/** @odoo-module **/

document.addEventListener('DOMContentLoaded', () => {
    const otpContainer = document.querySelector('.auth_otp_inputs');
    if (!otpContainer) {
        return;
    }

    const inputs = Array.from(otpContainer.querySelectorAll('.auth_otp_digit_input'));
    const hiddenTokenInput = document.getElementById('otp_token_hidden');
    const form = document.querySelector('.auth_otp_form');
    const resendBtn = document.getElementById('btn_resend_otp');
    const cooldownContainer = document.getElementById('cooldown_container');
    const cooldownTimerText = document.getElementById('cooldown_timer_text');

    function updateHiddenToken() {
        if (hiddenTokenInput) {
            hiddenTokenInput.value = inputs.map(input => input.value).join('');
        }
    }

    // Auto-focus first input on load
    if (inputs.length > 0) {
        inputs[0].focus();
    }

    inputs.forEach((input, index) => {
        // Keydown event for backspace and navigation
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace') {
                if (!input.value && index > 0) {
                    inputs[index - 1].focus();
                    inputs[index - 1].value = '';
                } else {
                    input.value = '';
                }
                updateHiddenToken();
                e.preventDefault();
            } else if (e.key === 'ArrowLeft' && index > 0) {
                inputs[index - 1].focus();
            } else if (e.key === 'ArrowRight' && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
        });

        // Input event for typing digits
        input.addEventListener('input', (e) => {
            const value = input.value.replace(/[^0-9]/g, '');
            input.value = value ? value.charAt(value.length - 1) : '';

            if (input.value && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
            updateHiddenToken();

            // Auto submit if all inputs filled
            if (inputs.every(inp => inp.value.length === 1)) {
                if (form) {
                    form.submit();
                }
            }
        });

        // Paste event for pasting complete OTP
        input.addEventListener('paste', (e) => {
            e.preventDefault();
            const pasteData = (e.clipboardData || window.clipboardData).getData('text');
            const digits = pasteData.replace(/[^0-9]/g, '').split('');

            if (digits.length > 0) {
                digits.forEach((digit, dIdx) => {
                    if (index + dIdx < inputs.length) {
                        inputs[index + dIdx].value = digit;
                    }
                });

                const targetIndex = Math.min(index + digits.length, inputs.length - 1);
                inputs[targetIndex].focus();
                updateHiddenToken();

                if (inputs.every(inp => inp.value.length === 1)) {
                    if (form) {
                        form.submit();
                    }
                }
            }
        });
    });

    // Resend Cooldown Timer Logic
    if (cooldownContainer) {
        let remainingSeconds = parseInt(cooldownContainer.getAttribute('data-remaining') || '0', 10);
        if (remainingSeconds > 0) {
            const timerInterval = setInterval(() => {
                remainingSeconds -= 1;
                if (cooldownTimerText) {
                    cooldownTimerText.textContent = remainingSeconds;
                }

                if (remainingSeconds <= 0) {
                    clearInterval(timerInterval);
                    if (resendBtn) {
                        resendBtn.removeAttribute('disabled');
                    }
                    cooldownContainer.innerHTML = '';
                }
            }, 1000);
        }
    }
});
