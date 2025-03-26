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
    alert("Logging out...");
    // Implement logout logic here
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

