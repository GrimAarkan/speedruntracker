document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const loadingEl = document.getElementById('loading');
    const recordDataEl = document.getElementById('record-data');
    const errorMessageEl = document.getElementById('error-message');
    const recordTimeEl = document.getElementById('record-time');
    const runnerEl = document.getElementById('runner');
    const dateEl = document.getElementById('date');
    const lastUpdatedEl = document.getElementById('last-updated');
    const refreshBtn = document.getElementById('refresh-btn');
    const categoryTitleEl = document.getElementById('category-title');
    const categoryInfoTitleEl = document.getElementById('category-info-title');
    const categoryDescriptionEl = document.getElementById('category-description');
    const allCategoriesTableEl = document.getElementById('all-categories-table');
    
    // Category descriptions
    const categoryDescriptions = {
        'any': 'Any% is a speedrunning category where the goal is to complete the game as quickly as possible without restrictions. This means using any glitches, exploits or shortcuts that are allowed by the community rules.',
        'all_chapters': 'All Chapters requires the player to complete all main chapters of the game in sequence, without skipping any major sections.',
        'glitchless': 'Glitchless runs prohibit the use of any exploits, glitches, or unintended mechanics. The game must be completed as the developers intended.',
        'no_oob': 'No OoB (Out of Bounds) runs allow most glitches but prohibit going outside the intended playable area of the game.',
        '100': '100% requires completing all objectives, collecting all documents and recordings, and experiencing all content in the game.',
        'glitchless_100': 'Glitchless 100% combines the requirements of both Glitchless and 100% categories - collecting everything without using any glitches.',
        'no_major_glitches': 'No Major Glitches allows minor exploits but prohibits significant glitches that dramatically change the intended gameplay.',
        'insane': 'Insane requires completing the game on the hardest difficulty setting (Insane mode), where death means starting over from the beginning.'
    };
    
    // Currently selected category
    let currentCategory = 'any';
    
    // Function to fetch world record data for a specific category
    function fetchCategoryRecord(categoryKey) {
        // Update current category
        currentCategory = categoryKey;
        
        // Show loading and hide any previous data/errors
        loadingEl.classList.remove('d-none');
        recordDataEl.classList.add('d-none');
        errorMessageEl.classList.add('d-none');
        
        fetch(`/api/outlast/category/${categoryKey}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('API request failed');
                }
                return response.json();
            })
            .then(data => {
                // Update the UI with the data
                categoryTitleEl.innerHTML = `<i class="fas fa-trophy me-2"></i>${data.category} World Record`;
                recordTimeEl.textContent = data.formatted_time;
                runnerEl.textContent = data.runner;
                dateEl.textContent = data.date;
                
                // Update category info
                categoryInfoTitleEl.textContent = `What is ${data.category}?`;
                categoryDescriptionEl.textContent = categoryDescriptions[categoryKey] || 
                    'This category has specific rules set by the speedrunning community.';
                
                // Update the last updated timestamp
                const now = new Date();
                lastUpdatedEl.textContent = now.toLocaleTimeString();
                
                // Hide loading and show the data
                loadingEl.classList.add('d-none');
                recordDataEl.classList.remove('d-none');
                
                // Add animation class
                recordDataEl.classList.add('fade-in-up');
                setTimeout(() => {
                    recordDataEl.classList.remove('fade-in-up');
                }, 500);
            })
            .catch(error => {
                console.error('Error fetching category record:', error);
                // Hide loading and show error message
                loadingEl.classList.add('d-none');
                errorMessageEl.classList.remove('d-none');
            });
    }
    
    // Function to fetch all categories data
    function fetchAllCategories() {
        fetch('/api/outlast/categories')
            .then(response => {
                if (!response.ok) {
                    throw new Error('API request failed');
                }
                return response.json();
            })
            .then(data => {
                // Clear loading row
                allCategoriesTableEl.innerHTML = '';
                
                // Sort categories by time (fastest first)
                const sortedCategories = Object.keys(data)
                    .filter(key => data[key] !== null)
                    .sort((a, b) => {
                        if (!data[a] || !data[b]) return 0;
                        return data[a].raw_time - data[b].raw_time;
                    });
                
                // Add rows for each category
                sortedCategories.forEach(key => {
                    const record = data[key];
                    if (record) {
                        const row = document.createElement('tr');
                        row.classList.add('category-row');
                        row.dataset.category = key;
                        
                        row.innerHTML = `
                            <td>
                                <strong>${record.category}</strong>
                                ${key === currentCategory ? '<span class="badge bg-danger ms-2">Selected</span>' : ''}
                            </td>
                            <td class="text-monospace">${record.detailed_time}</td>
                            <td>${record.runner}</td>
                            <td>${record.date}</td>
                        `;
                        
                        // Add click event to row
                        row.addEventListener('click', () => {
                            document.getElementById(`btn-${key}`).checked = true;
                            fetchCategoryRecord(key);
                            
                            // Update selected badge
                            document.querySelectorAll('.category-row').forEach(r => {
                                const badge = r.querySelector('.badge');
                                if (badge) badge.remove();
                                
                                if (r.dataset.category === key) {
                                    const catCell = r.querySelector('td:first-child');
                                    const newBadge = document.createElement('span');
                                    newBadge.className = 'badge bg-danger ms-2';
                                    newBadge.textContent = 'Selected';
                                    catCell.appendChild(newBadge);
                                }
                            });
                        });
                        
                        allCategoriesTableEl.appendChild(row);
                    }
                });
            })
            .catch(error => {
                console.error('Error fetching all categories:', error);
                allCategoriesTableEl.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center text-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Error loading category data
                        </td>
                    </tr>
                `;
            });
    }
    
    // Set up category button handlers
    document.querySelectorAll('input[name="category"]').forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                fetchCategoryRecord(this.value);
            }
        });
    });
    
    // Setup refresh button
    refreshBtn.addEventListener('click', function() {
        // Add spinner to button during refresh
        const originalContent = refreshBtn.innerHTML;
        refreshBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Refreshing...';
        refreshBtn.disabled = true;
        
        // Refresh current category and all categories
        fetchCategoryRecord(currentCategory);
        fetchAllCategories();
        
        // Reset button after a short delay
        setTimeout(() => {
            refreshBtn.innerHTML = originalContent;
            refreshBtn.disabled = false;
        }, 1000);
    });
    
    // Fetch data on page load
    fetchCategoryRecord('any');
    fetchAllCategories();
});
