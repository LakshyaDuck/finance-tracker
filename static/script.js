// ==========================================
// FORTUNA - Finance Tracker
// Global JavaScript Functions
// ==========================================

// Cookie Helper Functions (CS50 Compatible)
// ==========================================

function setCookie(name, value, days) {
    const expires = new Date();
    expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
    document.cookie = name + '=' + value + ';expires=' + expires.toUTCString() + ';path=/';
}

function getCookie(name) {
    const nameEQ = name + '=';
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

// Theme Management
// ==========================================

// Apply saved theme on page load
document.addEventListener('DOMContentLoaded', function() {
    const savedTheme = getCookie('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
});

// Mobile Navigation Toggle
// ==========================================

const navToggle = document.getElementById('navToggle');
const navMenu = document.getElementById('navMenu');

if (navToggle && navMenu) {
    navToggle.addEventListener('click', function() {
        navToggle.classList.toggle('active');
        navMenu.classList.toggle('active');
    });

    // Close mobile menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!navToggle.contains(e.target) && !navMenu.contains(e.target)) {
            navToggle.classList.remove('active');
            navMenu.classList.remove('active');
        }
    });

    // Close mobile menu when window is resized to desktop
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            navToggle.classList.remove('active');
            navMenu.classList.remove('active');
        }
    });
}

// Form Validation Helpers
// ==========================================

function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;

    return form.checkValidity();
}

// Auto-dismiss alerts after 5 seconds
// ==========================================

document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.remove();
            }, 300);
        }, 5000);
    });
});

// Confirm Delete Actions
// ==========================================

function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this?');
}

// Number Formatting
// ==========================================

function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

// Console log for debugging (remove in production)
// ==========================================

console.log('Fortuna Finance Tracker - Script loaded successfully');
console.log('Current theme:', getCookie('theme') || 'light');
