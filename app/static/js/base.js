function toggleSidebar() {
    document.addEventListener("DOMContentLoaded", function () {
        const sidebar = document.getElementById("sidebar");
        const burger = document.querySelector(".burger");
    
        // Toggle sidebar when clicking burger
        burger.addEventListener("click", function (event) {
            sidebar.classList.toggle("open");
            event.stopPropagation(); // Prevents immediate closing
        });
    
        // Close sidebar when clicking outside
        document.addEventListener("click", function (event) {
            if (window.innerWidth <= 768) { // Only apply on mobile
                if (!sidebar.contains(event.target) && !burger.contains(event.target)) {
                    sidebar.classList.remove("open");
                }
            }
        });
    
        // Prevent sidebar clicks from closing itself
        sidebar.addEventListener("click", function (event) {
            event.stopPropagation();
        });
    });

    let sidebar = document.getElementById("sidebar");
    let burger = document.querySelector(".burger");

    if (sidebar.classList.contains("open")) {
        sidebar.classList.remove("open");
        burger.classList.remove("active");
    } else {
        sidebar.classList.add("open");
        burger.classList.add("active");
    }
}

function logout() {
    // Close sidebar before showing logout modal
    let sidebar = document.getElementById("sidebar");
    let burger = document.querySelector(".burger");
    sidebar.classList.remove("open");
    burger.classList.remove("active");

    $('#logoutModal').modal('show');
}

function confirmLogout() {
    // Perform logout action here
    // For example, you might want to make an API call to logout
    // and then redirect to the login page
    window.location.href = '/logout';  // Replace with your actual logout URL
}

document.addEventListener("DOMContentLoaded", function () {
    // Get current page URL path
    const currentPath = window.location.pathname;

    // Loop through all sidebar links
    document.querySelectorAll(".nav-link").forEach(link => {
        if (link.getAttribute("href") === currentPath) {
            link.classList.add("active");
        }
    });
});