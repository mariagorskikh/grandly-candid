// Wait for the DOM to be loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, setting up event listeners');
    
    // Add submit event listener to the form
    const form = document.getElementById('search-form');
    if (form) {
        form.addEventListener('submit', handleSearch);
        console.log('Added submit listener to search form');
    } else {
        console.error('Could not find search form');
    }
});

async function handleSearch(event) {
    event.preventDefault();
    console.log('Form submitted');

    const form = event.target;
    const formData = new FormData(form);
    const searchParams = {};

    // Process form data
    for (let [key, value] of formData.entries()) {
        if (value && value.trim()) { // Only include non-empty values
            // Handle array parameters
            if (['year', 'subject', 'population', 'support', 'transaction'].includes(key)) {
                const values = value.split(',')
                    .map(v => v.trim())
                    .filter(v => v);
                if (values.length > 0) {
                    searchParams[key] = values;
                }
            } else if (['min_amt', 'max_amt'].includes(key)) {
                const numValue = parseInt(value);
                if (!isNaN(numValue)) {
                    searchParams[key] = numValue;
                }
            } else if (key === 'include_gov') {
                searchParams[key] = value === 'true';
            } else {
                searchParams[key] = value.trim();
            }
        }
    }

    console.log('Search parameters:', searchParams);
    await searchGrants(searchParams);
}

async function searchGrants(params = {}) {
    console.log('searchGrants called with params:', params);
    const resultsDiv = document.getElementById('results');
    
    if (!resultsDiv) {
        console.error('Could not find results div');
        return;
    }

    try {
        // Show loading state
        resultsDiv.innerHTML = `
            <div class="flex justify-center items-center py-12">
                <div class="animate-spin rounded-full h-12 w-12 border-4 border-orange-500 border-t-transparent"></div>
            </div>
        `;
        
        const response = await fetch('/search_grants', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(params)
        });

        console.log('Response received:', response.status);
        const data = await response.json();
        console.log('Data received:', data);
        
        if (response.ok) {
            displayResults(data);
        } else {
            console.error('Error response:', data);
            resultsDiv.innerHTML = `
                <div class="bg-white rounded-xl shadow-lg p-6">
                    <div class="text-red-500 mb-4">
                        <div class="font-bold text-lg">${escapeHtml(data.error || 'Unknown error')}</div>
                        ${data.details ? `<div class="mt-2 text-gray-600">${escapeHtml(data.details)}</div>` : ''}
                    </div>
                    <div class="text-gray-500 text-sm">
                        Try modifying your search criteria or using different keywords.
                    </div>
                </div>`;
        }
    } catch (error) {
        console.error('Error in searchGrants:', error);
        resultsDiv.innerHTML = `
            <div class="bg-white rounded-xl shadow-lg p-6">
                <div class="text-red-500">
                    <div class="font-bold text-lg">Failed to fetch results</div>
                    <div class="mt-2 text-gray-600">Error: ${escapeHtml(error.message)}</div>
                </div>
            </div>`;
    }
}

function displayResults(data) {
    console.log('Displaying results:', data);
    const resultsDiv = document.getElementById('results');
    
    if (!data.funders || data.funders.length === 0) {
        resultsDiv.innerHTML = `
            <div class="result-card rounded-xl shadow-lg p-8 text-center">
                <div class="text-5xl mb-4">🔍</div>
                <div class="text-xl font-medium text-gray-700 mb-2">No funders found</div>
                <div class="text-gray-500">
                    Try adjusting your search terms or removing some filters
                </div>
            </div>`;
        return;
    }

    const funders = data.funders;
    const meta = data.meta || {};

    let html = `
        <div class="space-y-6">
            <div class="result-card rounded-xl shadow-lg p-6 mb-4">
                <div class="text-2xl font-semibold result-title mb-2">
                    Found ${formatNumber(meta.total_hits || funders.length)} Funders
                </div>
                <div class="text-gray-500">
                    Showing ${funders.length} results per page
                </div>
            </div>
            
            <div class="space-y-6">
    `;

    funders.forEach(funder => {
        html += `
            <div class="result-card rounded-xl shadow-lg p-6 transform transition-all duration-300 hover:shadow-xl hover:scale-[1.02]">
                <h3 class="text-xl font-semibold result-title mb-4">
                    ${escapeHtml(funder.funder_name) || 'Unnamed Funder'}
                </h3>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <div class="result-label text-sm uppercase tracking-wide mb-1">EIN</div>
                        <div class="result-value font-medium">${escapeHtml(funder.ein) || 'N/A'}</div>
                    </div>
                    
                    <div>
                        <div class="result-label text-sm uppercase tracking-wide mb-1">Location</div>
                        <div class="result-value font-medium">${[
                            funder.funder_city, 
                            funder.funder_state, 
                            funder.funder_country
                        ].filter(Boolean).map(escapeHtml).join(', ') || 'N/A'}</div>
                    </div>
                
                    <div>
                        <div class="result-label text-sm uppercase tracking-wide mb-1">Number of Grants</div>
                        <div class="result-value font-medium">${formatNumber(funder.grant_count)}</div>
                    </div>
                    
                    <div>
                        <div class="result-label text-sm uppercase tracking-wide mb-1">Total Amount</div>
                        <div class="result-value font-medium">$${formatMoney(funder.amount_usd)}</div>
                    </div>
                </div>

                <div class="mt-6 flex flex-wrap gap-4">
                    ${funder.funder_profile_url ? `
                        <a href="${escapeHtml(funder.funder_profile_url)}" 
                           target="_blank" 
                           class="search-button inline-flex items-center px-4 py-2 text-white rounded-lg transition-all duration-300">
                            <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                                <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                            </svg>
                            View on Candid
                        </a>
                    ` : ''}
                    
                    <a href="https://www.google.com/search?q=${encodeURIComponent(funder.funder_name)}" 
                       target="_blank" 
                       class="inline-flex items-center px-4 py-2 bg-white border-2 border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 hover:border-gray-300 transition-all duration-300">
                        <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
                        </svg>
                        Search on Google
                    </a>
                </div>
            </div>
        `;
    });

    html += `
            </div>
            
            ${meta.total_hits > funders.length ? `
            <div class="text-center text-gray-600 mt-8 font-medium">
                Showing ${funders.length} of ${formatNumber(meta.total_hits)} funders
            </div>
            ` : ''}
        </div>
    `;

    resultsDiv.innerHTML = html;
}

function formatMoney(amount) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

function formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
}

function escapeHtml(unsafe) {
    if (unsafe == null) return '';
    return unsafe
        .toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
