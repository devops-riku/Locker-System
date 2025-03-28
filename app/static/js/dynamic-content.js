document.addEventListener('DOMContentLoaded', function() {
    const mainContent = document.getElementById('main-content');
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.getAttribute('data-page');
            loadContent(page);
        });
    });

    function loadContent(page) {
        axios.get(`/${page}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            mainContent.innerHTML = response.data;
            history.pushState(null, '', `/${page}`);
            
            // Execute any scripts in the loaded content
            const scripts = mainContent.getElementsByTagName('script');
            for (let script of scripts) {
                eval(script.innerHTML);
            }
        })
        .catch(error => {
            console.error('Error loading content:', error);
        });
    }
});