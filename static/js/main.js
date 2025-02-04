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

function displayResults(results) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = ''; // Clear previous results
    
    if (!results.funders || results.funders.length === 0) {
        resultsDiv.innerHTML = '<p class="text-gray-600 text-center py-4">No results found</p>';
        return;
    }
    
    // Display each funder
    results.funders.forEach(funder => {
        const card = document.createElement('div');
        card.className = 'bg-white rounded-lg shadow-lg p-6 mb-6 hover:shadow-xl transition-shadow duration-200';
        
        // Header section with name and EIN
        const nameSection = document.createElement('div');
        nameSection.className = 'mb-4';
        nameSection.innerHTML = `
            <h2 class="text-2xl font-bold text-indigo-900 mb-2">${funder.funder_name || 'Unnamed Funder'}</h2>
            ${funder.ein ? `<p class="text-sm text-gray-600">EIN: ${funder.ein}</p>` : ''}
        `;
        
        // Location and Website section
        const detailsSection = document.createElement('div');
        detailsSection.className = 'grid grid-cols-2 gap-4 mb-4';
        
        let websiteHtml = '';
        if (funder.url) {
            websiteHtml = `
                <a href="${funder.url}" target="_blank" rel="noopener noreferrer" 
                   class="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
                    <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    Visit Website
                </a>`;
        }
        
        detailsSection.innerHTML = `
            <div>
                <h3 class="font-semibold text-gray-700">Location</h3>
                <p class="text-gray-600">${funder.funder_city || 'N/A'}, ${funder.funder_state || 'N/A'}</p>
            </div>
            <div class="flex items-center">
                ${websiteHtml}
            </div>
        `;
        
        // AI Summary section
        const summarySection = document.createElement('div');
        summarySection.className = 'mt-4';
        if (funder.ai_summary) {
            summarySection.innerHTML = `
                <div class="bg-gradient-to-r from-purple-50 to-indigo-50 p-4 rounded-lg">
                    <h3 class="text-lg font-semibold text-indigo-900 mb-2">AI-Generated Summary</h3>
                    <p class="text-gray-700">${funder.ai_summary}</p>
                    <p class="text-xs text-gray-500 mt-2">Source: ${funder.summary_source || 'AI Analysis'}</p>
                </div>
            `;
        }
        
        // Recent Giving section (if available)
        const grantsSection = document.createElement('div');
        if (funder.amount_usd) {
            grantsSection.className = 'mt-4 p-4 bg-green-50 rounded-lg';
            grantsSection.innerHTML = `
                <h3 class="font-semibold text-green-800">Recent Giving</h3>
                <p class="text-green-700">${formatCurrency(funder.amount_usd)}</p>
            `;
        }
        
        // Assemble the card
        card.appendChild(nameSection);
        card.appendChild(detailsSection);
        card.appendChild(summarySection);
        if (funder.amount_usd) {
            card.appendChild(grantsSection);
        }
        
        resultsDiv.appendChild(card);
    });
    
    // Show total results count
    const countDiv = document.createElement('div');
    countDiv.className = 'text-center text-gray-600 mt-4';
    countDiv.textContent = `Found ${results.meta.total_hits} results`;
    resultsDiv.insertBefore(countDiv, resultsDiv.firstChild);
}

function formatCurrency(amount) {
    if (!amount) return 'N/A';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
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
