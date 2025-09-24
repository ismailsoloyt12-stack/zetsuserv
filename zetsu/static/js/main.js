/**
 * ZetsuServ Main JavaScript
 * Handles form validation, mobile menu, and interactive features
 */

document.addEventListener('DOMContentLoaded', function() {
    // Mobile Menu Toggle
    initMobileMenu();
    
    // Smooth Scroll for Anchor Links
    initSmoothScroll();
    
    // Form Validation Enhancement
    initFormValidation();
    
    // Auto-dismiss Flash Messages
    initFlashMessages();
});

/**
 * Initialize Mobile Menu
 */
function initMobileMenu() {
    const navToggle = document.getElementById('navToggle');
    const mobileMenu = document.getElementById('mobileMenu');
    
    if (navToggle && mobileMenu) {
        navToggle.addEventListener('click', function() {
            mobileMenu.classList.toggle('active');
            this.classList.toggle('active');
        });
        
        // Close mobile menu when clicking on a link
        const mobileLinks = mobileMenu.querySelectorAll('.mobile-link');
        mobileLinks.forEach(link => {
            link.addEventListener('click', function() {
                mobileMenu.classList.remove('active');
                navToggle.classList.remove('active');
            });
        });
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', function(event) {
            if (!navToggle.contains(event.target) && !mobileMenu.contains(event.target)) {
                mobileMenu.classList.remove('active');
                navToggle.classList.remove('active');
            }
        });
    }
}

/**
 * Initialize Smooth Scroll for Anchor Links
 */
function initSmoothScroll() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            if (href !== '#' && href !== '#0') {
                const target = document.querySelector(href);
                
                if (target) {
                    e.preventDefault();
                    const offset = 80; // Navbar height
                    const targetPosition = target.offsetTop - offset;
                    
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            }
        });
    });
}

/**
 * Initialize Form Validation Enhancement
 */
function initFormValidation() {
    // Request Form Validation
    const requestForm = document.getElementById('requestForm');
    if (requestForm) {
        enhanceRequestForm(requestForm);
    }
    
    // Login Form Validation
    const loginForm = document.querySelector('.login-form');
    if (loginForm) {
        enhanceLoginForm(loginForm);
    }
}

/**
 * Enhance Request Form
 */
function enhanceRequestForm(form) {
    const inputs = form.querySelectorAll('input, select, textarea');
    
    // Add real-time validation
    inputs.forEach(input => {
        // Remove error on input
        input.addEventListener('input', function() {
            this.classList.remove('is-invalid');
        });
        
        // Validate on blur
        input.addEventListener('blur', function() {
            validateField(this);
        });
    });
    
    // Character counter for textarea
    const detailsField = form.querySelector('#details');
    if (detailsField) {
        const formText = detailsField.closest('.form-group').querySelector('.form-text');
        
        detailsField.addEventListener('input', function() {
            const length = this.value.trim().length;
            if (formText) {
                if (length < 20) {
                    formText.textContent = `${length}/20 characters (minimum 20 required)`;
                    formText.style.color = '#dc2626';
                } else {
                    formText.textContent = `${length} characters`;
                    formText.style.color = '';
                }
            }
        });
    }
    
    // File upload preview
    const fileInput = form.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const files = this.files;
            const fileWrapper = this.closest('.file-upload-wrapper');
            let fileList = fileWrapper.querySelector('.file-list');
            
            if (!fileList) {
                fileList = document.createElement('div');
                fileList.className = 'file-list';
                fileWrapper.appendChild(fileList);
            }
            
            fileList.innerHTML = '';
            
            if (files.length > 0) {
                const listEl = document.createElement('ul');
                listEl.style.marginTop = '10px';
                listEl.style.listStyle = 'none';
                
                Array.from(files).forEach(file => {
                    const li = document.createElement('li');
                    li.style.padding = '5px 0';
                    li.style.color = '#6b7280';
                    li.textContent = `📎 ${file.name} (${formatFileSize(file.size)})`;
                    listEl.appendChild(li);
                });
                
                fileList.appendChild(listEl);
            }
        });
    }
}

/**
 * Enhance Login Form
 */
function enhanceLoginForm(form) {
    const inputs = form.querySelectorAll('input');
    
    inputs.forEach(input => {
        input.addEventListener('input', function() {
            this.classList.remove('is-invalid');
        });
    });
}

/**
 * Validate Individual Field
 */
function validateField(field) {
    const value = field.value.trim();
    let isValid = true;
    
    // Check if required
    if (field.hasAttribute('required') && !value) {
        isValid = false;
    }
    
    // Email validation
    if (field.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            isValid = false;
        }
    }
    
    // Phone validation
    if (field.id === 'phone' && value) {
        if (value.length < 10) {
            isValid = false;
        }
    }
    
    // Number validation
    if (field.type === 'number') {
        const min = parseInt(field.getAttribute('min'));
        const max = parseInt(field.getAttribute('max'));
        const numValue = parseInt(value);
        
        if (isNaN(numValue) || numValue < min || numValue > max) {
            isValid = false;
        }
    }
    
    // Textarea minimum length
    if (field.tagName === 'TEXTAREA' && field.id === 'details') {
        if (value.length < 20) {
            isValid = false;
        }
    }
    
    if (!isValid) {
        field.classList.add('is-invalid');
    } else {
        field.classList.remove('is-invalid');
    }
    
    return isValid;
}

/**
 * Format File Size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Initialize Flash Messages Auto-Dismiss
 */
function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');
    
    flashMessages.forEach(message => {
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            message.style.animation = 'fadeOut 0.5s ease';
            setTimeout(() => {
                message.remove();
            }, 500);
        }, 5000);
    });
}

/**
 * Add CSS Animation for Flash Messages
 */
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from { opacity: 1; transform: translateX(0); }
        to { opacity: 0; transform: translateX(100%); }
    }
    
    .nav-toggle.active span:nth-child(1) {
        transform: rotate(45deg) translate(5px, 5px);
    }
    
    .nav-toggle.active span:nth-child(2) {
        opacity: 0;
    }
    
    .nav-toggle.active span:nth-child(3) {
        transform: rotate(-45deg) translate(7px, -6px);
    }
    
    .nav-toggle span {
        transition: all 0.3s ease;
    }
`;
document.head.appendChild(style);

/**
 * Utility Functions
 */
const Utils = {
    /**
     * Debounce function to limit function calls
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    /**
     * Check if element is in viewport
     */
    isInViewport: function(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }
};

/**
 * Handle Scroll Events
 */
let lastScroll = 0;
const navbar = document.querySelector('.navbar');

window.addEventListener('scroll', Utils.debounce(function() {
    const currentScroll = window.pageYOffset;
    
    if (navbar) {
        if (currentScroll > lastScroll && currentScroll > 100) {
            // Scrolling down
            navbar.style.transform = 'translateY(-100%)';
        } else {
            // Scrolling up
            navbar.style.transform = 'translateY(0)';
        }
        
        // Add shadow on scroll
        if (currentScroll > 50) {
            navbar.style.boxShadow = '0 4px 20px rgba(0,0,0,0.08)';
        } else {
            navbar.style.boxShadow = '';
        }
    }
    
    lastScroll = currentScroll;
}, 100));

// Add smooth transition to navbar
if (navbar) {
    navbar.style.transition = 'transform 0.3s ease, box-shadow 0.3s ease';
}