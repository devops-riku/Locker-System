
document.addEventListener('click', function(event) {
    const dropdowns = document.querySelectorAll('.dropdown-menu');
    dropdowns.forEach(dropdown => {
        if (!dropdown.contains(event.target) && !event.target.matches('.action-button')) {
            dropdown.style.display = 'none';
        }
    });
});

document.addEventListener("DOMContentLoaded", function () {
const togglePassword = document.querySelector('#togglePassword');
const togglePin = document.querySelector('#togglePin');
const password = document.querySelector('#password');
const pin = document.querySelector('#pin_number');
const pinInput = document.querySelector('#pin_number');
const strengthMeter = document.querySelector('.progress-bar');
const strengthText = document.querySelector('.strength-text');

populateLockerList();

// Toggle PIN visibility
document.getElementById('toggleEditPin').addEventListener('click', function() {
    const pinInput = document.getElementById('editPinNumber');
    const type = pinInput.getAttribute('type') === 'password' ? 'text' : 'password';
    pinInput.setAttribute('type', type);
    this.querySelector('i').classList.toggle('fa-eye');
    this.querySelector('i').classList.toggle('fa-eye-slash');
  });


togglePassword.addEventListener('click', function (e) {
    // Toggle the type attribute
    const type = password.getAttribute('type') === 'password' ? 'text' : 'password';
    password.setAttribute('type', type);
    // Toggle the eye icon
    this.querySelector('i').classList.toggle('fa-eye');
    this.querySelector('i').classList.toggle('fa-eye-slash');
});

togglePin.addEventListener('click', function (e) {
    // Toggle the type attribute
    const type = pin.getAttribute('type') === 'password' ? 'text' : 'password';
    pin.setAttribute('type', type);
    // Toggle the eye icon
    this.querySelector('i').classList.toggle('fa-eye');
    this.querySelector('i').classList.toggle('fa-eye-slash');
});

// Password strength meter
password.addEventListener('input', function() {
    const strength = calculatePasswordStrength(this.value);
    updateStrengthMeter(strength);
});

function calculatePasswordStrength(password) {
    let strength = 0;
    let hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);

    if (password.length >= 8) {
        strength += 25;
        if (hasSpecialChar) strength += 25;
        if (password.match(/[a-z]+/)) strength += 25;
        if (password.match(/[A-Z]+/)) strength += 25;
        if (password.match(/[0-9]+/)) strength += 25;
    } else {
        // If password is less than 8 characters, strength remains 0
        return 0;
    }

    // Normalize strength to 100
    return Math.min(strength, 100);
}

function updateStrengthMeter(strength) {
    strengthMeter.style.width = strength + '%';
    strengthMeter.setAttribute('aria-valuenow', strength);
    
    if (strength < 50) {
        strengthMeter.classList.remove('bg-warning', 'bg-success');
        strengthMeter.classList.add('bg-danger');
    } else if (strength < 75) {
        strengthMeter.classList.remove('bg-danger', 'bg-success');
        strengthMeter.classList.add('bg-warning');
    } else {
        strengthMeter.classList.remove('bg-danger', 'bg-warning');
        strengthMeter.classList.add('bg-success');
    }

    // Update the strength text
    if (strength === 0) {
        strengthText.textContent = 'Too weak';
        strengthText.style.color = '#dc3545'; // red
    } else if (strength < 50) {
        strengthText.textContent = 'Weak';
        strengthText.style.color = '#dc3545'; // red
    } else if (strength < 75) {
        strengthText.textContent = 'Medium';
        strengthText.style.color = '#ffc107'; // yellow
    } else {
        strengthText.textContent = 'Strong';
        strengthText.style.color = '#28a745'; // green
    }
}

pinInput.addEventListener('input', function(e) {
    // Remove any non-digit characters
    this.value = this.value.replace(/\D/g, '');
    
    // Limit to 4 digits
    if (this.value.length > 4) {
        this.value = this.value.slice(0, 4);
    }
});

pinInput.addEventListener('keypress', function(e) {
    // Prevent non-digit input
    if (e.which < 48 || e.which > 57) {
        e.preventDefault();
    }
});

const grid = new gridjs.Grid({
    columns: [
        "Name",
        "Email",
        "RFID Serial Number",
        "Locker",
        {
            name: 'Actions',
            formatter: (cell, row) => {
                const userId = row.cells[4].data;
                // We'll need the is_active value from the data source, so fetch from row or data:
                const userIsActive = row.cells[5].data; // We'll add is_active as hidden 6th col below
                console.log(userIsActive);
                const activateButtonText = userIsActive ? 'Disable': 'Activate';

                return gridjs.h('div', {className: 'action-buttons'}, [
                gridjs.h('button', {
                    className: 'btn btn-sm btn-outline-primary me-1',
                    onClick: () => viewUser(userId)
                }, 'View'),
                gridjs.h('button', {
                    className: 'btn btn-sm btn-outline-secondary me-1',
                    onClick: () => editUser(userId)
                }, 'Edit'),
                gridjs.h('button', {
                    className: 'btn btn-sm btn-outline-danger me-1',
                    onClick: () => deleteUser(userId)
                }, 'Delete'),
                gridjs.h('button', {
                    className: 'btn btn-sm btn-outline-warning',
                    onClick: () => openActivateModal(userId, userIsActive)
                }, activateButtonText)
                ]);
            }
        },
        {
            name: 'User Is_Active',
            hidden: true 
        }

    ],
    server: {
        url: '/admin/user-lists',
       then: data => data.results.map(user => [
            `${user.Name}`,
            user.email,
            user.credentials[0]?.rfid_serial_number || 'Not Set',
            user.credentials[0]?.locker?.name || 'Not Assigned',
            user.id,
            user.is_active || false 
        ]),
        
        total: data => data.total
    },
    sort: true,
    pagination: {
        limit: 8,
        server: {
            url: (prev, page, limit) => {
                const page_number = page + 1; // Grid.js is 0-based, but your API expects 1-based
                return `${prev}?page_number=${page_number}&page_size=${limit}`;
            },
            total: data => data.total
        }
    },
    
    search: true,
    style: {
        table: {
            'border-collapse': 'collapse',
            'width': '100%',
            'background-color': '#1e1e1e'
        },
        th: {
            'background-color': '#252525',
            'color': '#e0e0e0',
            'border-bottom': '2px solid #333',
            'text-align': 'left',
            'padding': '12px'
        },
        td: {
            'background-color': '#2a2a2a',
            'color': '#e0e0e0',
            'border-bottom': '1px solid #333',
            'padding': '12px'
        }
    },
    className: {
        table: 'gridjs-table table-dark',
        thead: 'gridjs-thead',
        tbody: 'gridjs-tbody',
        th: 'gridjs-th',
        td: 'gridjs-td',
        footer: 'gridjs-footer bg-dark text-light',
        
        search: 'gridjs-search bg-dark text-light',
        loading: 'gridjs-loading bg-dark text-light',
        notFound: 'gridjs-notfound bg-dark text-light'
    }
}).render(document.getElementById("grid-table"));

// Add an event listener for the 'load' event
grid.on('load', () => {
    const paginationButtons = document.querySelectorAll('.gridjs-pages button');
    paginationButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Force a re-render after a short delay
            setTimeout(() => grid.forceRender(), 100);
        });
    });
});


// Add user functionality
document.getElementById('addUserForm').addEventListener('submit', function(e) {
    e.preventDefault();

    const first_name = document.getElementById('first_name').value;
    const last_name = document.getElementById('last_name').value;
    const address = document.getElementById('address').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const locker_number = document.getElementById('locker_number').value;
    const rfid_serial_number = document.getElementById('rfid_serial_number').value;
    const pin_number = document.getElementById('pin_number').value;
    
    const userData = {
        first_name,
        last_name,
        address,
        email,
        password,
        locker_number,
        rfid_serial_number,
        pin_number
    };

    axios.post('/admin/create-user', userData)
        .then(response => {
            toastr.success("User added successfully.");

            // Clear the form
            clearAddUserForm();

            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addUserModal'));
            if (modal) modal.hide();

            // Now re-render grid after successful toast
            grid.updateConfig({}).forceRender();
        })
        .catch(error => {
            console.error('Error adding user:', error);
            toastr.error('Error adding user. Please try again.');
        });
});

// Update user functionality
document.getElementById('editUserForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const id = document.getElementById('editUserId').value;
    const first_name = document.getElementById('editFirstName').value;
    const last_name = document.getElementById('editLastName').value;
    const email = document.getElementById('editEmail').value;

    const address = document.getElementById('editAddress').value;
    const assigned_locker = document.getElementById('editLocker').value;
    const pin_number = document.getElementById('editPinNumber').value;
    const rfid_serial_number = document.getElementById('editRfidSerialNumber').value;
    const is_active = document.getElementById('editIsActive').checked;

    const payload = {
        first_name,
        last_name,
        address,
        email,
        assigned_locker,
        pin_number,
        rfid_serial_number,
        is_active
    };

    axios.put(`/admin/user/${id}`, payload)
        .then(response => {
            toastr.success("User updated successfully.");

            const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
            if (modal) modal.hide();

            // Now re-render grid after successful toast
            grid.updateConfig({}).forceRender();
        })
        .catch(error => {
            console.error('Error updating user:', error);
            toastr.error("Failed to update user.");
        });
});

// Delete user functionality
document.getElementById('confirmDeleteUser').addEventListener('click', function (e) {
    e.preventDefault();

    const userId = this.dataset.userId;

    if (!userId) {
        toastr.error("User ID is missing.");
        return;
    }

    axios.delete(`/admin/user/${userId}`)
        .then(response => {
            toastr.success("User deleted successfully.");

            // Hide the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteUserModal'));
            modal.hide();

            // Now re-render grid after successful toast
            grid.updateConfig({}).forceRender();
        })
        .catch(error => {
            console.error("Delete error:", error);
            toastr.error("Failed to delete user.");
        });
});


let selectedUserIdForActivation = null;
  let selectedUserCurrentStatus = null;

  function openActivateModal(userId) {
    selectedUserIdForActivation = userId;

    // Fetch user info to get current active status
    axios.get(`/admin/user/${userId}`)
      .then(response => {
        const user = response.data;
        selectedUserCurrentStatus = user.is_active;

        // Update modal text dynamically
        const actionText = selectedUserCurrentStatus ? 'disable' : 'activate';
        document.getElementById('activateActionText').textContent = actionText;

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('activateUserModal'));
        modal.show();
      })
      .catch(error => {
        console.error('Failed to fetch user status:', error);
        toastr.error('Failed to load user status.');
      });
  }

  document.getElementById('confirmActivateBtn').addEventListener('click', function() {
    if (!selectedUserIdForActivation) return;

    // If user is currently active, next status is false (disable)
    // Else next status is true (activate)
    const newStatus = !selectedUserCurrentStatus;

    axios.put('/admin/set-account-active', {
      user_id: selectedUserIdForActivation,
      is_active: newStatus
    })
    .then(response => {
      toastr.success(`User has been ${newStatus ? 'activated' : 'disabled'} successfully.`);

      // Hide modal
      const modalEl = document.getElementById('activateUserModal');
      const modal = bootstrap.Modal.getInstance(modalEl);
      modal.hide();

      // Refresh grid data
      grid.updateConfig({}).forceRender();
    })
    .catch(error => {
      console.error('Error updating user status:', error);
      toastr.error('Failed to update user status.');
    });
  });

function clearAddUserForm() {
    document.getElementById('first_name').value = '';
    document.getElementById('last_name').value = '';
    document.getElementById('address').value = '';
    document.getElementById('email').value = '';
    document.getElementById('password').value = '';
    document.getElementById('rfid_serial_number').value = '';
    document.getElementById('pin_number').value = '';
    
    // Reset the password strength meter
    const strengthMeter = document.querySelector('.progress-bar');
    const strengthText = document.querySelector('.strength-text');
    if (strengthMeter && strengthText) {
        strengthMeter.style.width = '0%';
        strengthMeter.setAttribute('aria-valuenow', 0);
        strengthMeter.classList.remove('bg-danger', 'bg-warning', 'bg-success');
        strengthText.textContent = '';
    }
}
});

function showActions(event, id) {
event.stopPropagation();
const dropdown = document.getElementById(`dropdown-${id}`);

// Toggle display
if (dropdown.style.display === 'block') {
    dropdown.style.display = 'none';
} else {
    // Hide all other dropdowns
    const allDropdowns = document.querySelectorAll('.dropdown-menu');
    allDropdowns.forEach(d => d.style.display = 'none');

    // Show this dropdown
    dropdown.style.display = 'block';
    
    // Ensure the dropdown is visible within the viewport
    const dropdownRect = dropdown.getBoundingClientRect();
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    
    if (dropdownRect.bottom > viewportHeight) {
        dropdown.style.top = 'auto';
        dropdown.style.bottom = '100%';
    } else {
        dropdown.style.top = '100%';
        dropdown.style.bottom = 'auto';
    }
}
}

function viewUser(id) {
    // Fetch specific user data from the server
    fetch(`/admin/user/${id}`)
        .then(response => response.json())
        .then(user => {
            if (user) {
                const userDetailsHtml = `
                    <p><strong>Name:</strong> ${user.first_name} ${user.last_name}</p>
                    <p><strong>Email:</strong> ${user.email}</p>

                    <p><strong>Address:</strong> ${user.address}</p>
                    <p><strong>Assigned Locker:</strong> ${user.credentials[0]?.locker?.name || 'Not Assigned'}</p>
                    <p><strong>PIN Number:</strong> ${user.credentials[0]?.pin_number || 'Not Set'}</p>
                    <p><strong>RFID Serial Number:</strong> ${user.credentials[0]?.rfid_serial_number || 'Not Set'}</p>
                `;
                document.getElementById('userDetails').innerHTML = userDetailsHtml;

                // Show the modal
                var modal = new bootstrap.Modal(document.getElementById('viewUserModal'));
                modal.show();
            } else {
                console.error('User not found');
            }
        })
        .catch(error => console.error('Error fetching user details:', error));
}


function editUser(id) {
    Promise.all([
        fetch(`/admin/user/${id}`).then(res => res.json()),
        fetch('/admin/lockers').then(res => res.json())
    ])
    .then(([user, lockers]) => {
        document.getElementById('editUserId').value = user.id;
        document.getElementById('editFirstName').value = user.first_name;
        document.getElementById('editLastName').value = user.last_name;
        document.getElementById('editEmail').value = user.email;
        document.getElementById('editAddress').value = user.address;
        document.getElementById('editPinNumber').value = user.credentials[0]?.pin_number || '';
        document.getElementById('editRfidSerialNumber').value = user.credentials[0]?.rfid_serial_number || '';
        
        // Set the is_active toggle
        document.getElementById('editIsActive').checked = user.credentials[0]?.is_active || false;


        const lockerSelect = document.getElementById('editLocker');
        lockerSelect.innerHTML = '';

        // Create option groups
        const availableGroup = document.createElement('optgroup');
        availableGroup.label = 'Available';
        const notAvailableGroup = document.createElement('optgroup');
        notAvailableGroup.label = 'Not Available';

        // Add a default "Choose Locker" option
        const defaultOption = document.createElement('option');
        defaultOption.value = "";
        defaultOption.textContent = "Choose Locker";
        defaultOption.disabled = true;
        lockerSelect.appendChild(defaultOption);

        lockers.forEach(locker => {
            const option = document.createElement('option');
            option.value = locker.id;
            option.textContent = locker.name;

            if (locker.is_available || locker.id === user.credentials[0]?.locker?.id) {
                availableGroup.appendChild(option);
            } else {
                option.disabled = true;
                notAvailableGroup.appendChild(option);
            }

            if (locker.id === user.credentials[0]?.locker?.id) {
                option.selected = true;
            }
        });

        // Add groups to select element
        if (availableGroup.children.length > 0) {
            lockerSelect.appendChild(availableGroup);
        }
        if (notAvailableGroup.children.length > 0) {
            lockerSelect.appendChild(notAvailableGroup);
        }

        const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
        modal.show();
    })
    .catch(error => {
        console.error('Error loading user or lockers:', error);
        toastr.error("Failed to load user details or lockers.");
    });
}


function deleteUser(id) {
    fetch(`/admin/user/${id}`)
        .then(res => res.json())
        .then(user => {
            const fullName = `${user.first_name} ${user.last_name}`;
            document.getElementById('deleteUserName').textContent = fullName;

            const deleteBtn = document.getElementById('confirmDeleteUser');
            deleteBtn.dataset.userId = id;

            const modal = new bootstrap.Modal(document.getElementById('deleteUserModal'));
            modal.show();
        })
        .catch(err => {
            console.error("Failed to load user info:", err);
            toastr.error("Failed to fetch user information.");
        });
}

function populateLockerList() {
    axios.get('/admin/lockers')
        .then(function (response) {
            const lockerSelect = document.getElementById('locker_number');
            lockerSelect.innerHTML = ''; // Clear existing options

            // Create option groups
            const availableGroup = document.createElement('optgroup');
            availableGroup.label = 'Available';
            const notAvailableGroup = document.createElement('optgroup');
            notAvailableGroup.label = 'Not Available';

            // Add a default "Choose Locker" option
            const defaultOption = document.createElement('option');
            defaultOption.value = "";
            defaultOption.textContent = "Choose Locker";
            defaultOption.selected = true;
            defaultOption.disabled = true;
            lockerSelect.appendChild(defaultOption);

            response.data.forEach(function(locker) {
                const option = document.createElement('option');
                option.value = locker.id;
                option.textContent = locker.name;

                if (locker.is_available) {
                    availableGroup.appendChild(option);
                } else {
                    option.disabled = true;
                    notAvailableGroup.appendChild(option);
                }
            });

            // Add groups to select element
            if (availableGroup.children.length > 0) {
                lockerSelect.appendChild(availableGroup);
            }
            if (notAvailableGroup.children.length > 0) {
                lockerSelect.appendChild(notAvailableGroup);
            }
        })
        .catch(function (error) {
            console.error('Error fetching lockers:', error);
        });
}





