const chemicalNameInput = document.getElementById("chemicalName");
const casNumberInput = document.getElementById("casNumber");
const verifiedResultContainer = document.getElementById("verifiedResults");
const unverifiedResultContainer = document.getElementById("unverifiedResults");
const searchingState = document.getElementById("searchingState");
const pdfContainer = document.getElementById("viewPdfContainer");
const pdfFrame = document.getElementById("pdfFrame");
const searchBtn = document.getElementById("searchBtn");

// In mobile devices :
const isMobileUser = window.innerWidth < 768;

// API (azure) URL
// const BASE_API_URL = "https://scout-api.azurewebsites.net/";
const BASE_API_URL = "https://viridium-scout.azurewebsites.net/";

// Display the search results
const displayResults = (results) => {
	// Insert verified in verified container and unverified into unverified container
	verifiedResultContainer.innerHTML = "";
	unverifiedResultContainer.innerHTML = "";
	let foundVerifiedPdf = false; // To check if any verified pdf is found

	results.forEach((result) => {
		// Extract filename and create a href link
		const filename = result.filepath.split("/").pop();
		const pdfUrl = BASE_API_URL + result.filepath; // construct a pdf url

		// Create a link
		const a = document.createElement("a");
		a.className = "response-link";
		a.href = pdfUrl;
		a.textContent = "🔗  " + filename;
		a.addEventListener("click", openPdfOnLinkClick);

		// Add into respective container
		if (result.verified) {
			verifiedResultContainer.append(a);
			foundVerifiedPdf = true;
		} else {
			// Check if it has a heading already, if not then add heading first !
			if (!unverifiedResultContainer.hasChildNodes()) {
				const h1 = document.createElement("h1");
				h1.className = "text-lg font-semibold";
				h1.textContent = "Suggestions";
				unverifiedResultContainer.append(h1);
			}
			unverifiedResultContainer.append(a);
		}
	});

	// If no verified pdf found, then show message
	!foundVerifiedPdf && (searchingState.textContent = "No verified PDF found");
};

// Make an API_CALL and return the results
const searchMsds = async (query) => {
	try {
		// urlStructure = `https://scout-api.azurewebsites.net/scout/query`
		let response = await fetch(`${BASE_API_URL}scout/${query}`);
		return await response.json();
	} catch (err) {
		console.log(err.message);
		return { error: err.message };
	}
};

// Handle form submit
const handleOnFormSubmit = async (e) => {
	e.preventDefault(); //prevent default behavior

	// disable button until the results are fetched
	searchBtn.textContent = "Searching...";
	searchBtn.disabled = true;

	// cleanups (clear previous results)
	verifiedResultContainer.innerHTML = "";
	unverifiedResultContainer.innerHTML = "";
	searchingState.textContent = "";
	pdfContainer.classList.add("hidden");

	// Get values
	const chemicalName = chemicalNameInput.value;
	const casNumber = casNumberInput.value;

	if (chemicalName === "" && casNumber === "") {
		searchingState.textContent =
			"Please enter either the Chemical Name or CAS number";
		searchBtn.textContent = "Search";
		searchBtn.disabled = false;
		return;
	}

	// Get what to search for
	const valueToSearch = chemicalName || casNumber;

	// Show searching state
	searchingState.textContent = `Searching for ${valueToSearch}...`;

	// search
	const result = await searchMsds(valueToSearch);

	// Check for errors
	if (result.error) {
		searchingState.textContent = "Something went wrong 😔";
		searchBtn.textContent = "Search";
		searchBtn.disabled = false;
		return;
	}

	// Show the status of the search
	if (result.length == 0) {
		searchingState.textContent = "No results found";
	} else {
		searchingState.textContent = "";
		// Insert the result in the response container
		displayResults(result);
	}

	// Re-enable button
	searchBtn.textContent = "Search";
	searchBtn.disabled = false;

	// scroll to bottom
	scrollToBottom();
};

// Handle pdf opening :
const openPdfOnLinkClick = (e) => {
	e.preventDefault();
	// Get the pdfURl and provide it to pdf frame.
	const pdfUrl = e.target.getAttribute("href");

	// Download the pdf for mobile users
	if (isMobileUser) {
		window.open(pdfUrl, "_blank");
	} else {
		// Show preview of pdf
		pdfFrame.src = pdfUrl;
		// Display the pdf viewer
		pdfContainer.classList.remove("hidden");
		// scroll to top
		scrollToTop();
	}
};

// Handle pdf closing
const closePdfViewer = () => {
	pdfContainer.classList.add("hidden");
	pdfFrame.src = "";
};

// Handle scrolling to top
const scrollToTop = () => {
	document.body.scrollTop = 0;
	document.documentElement.scrollTop = 0;
};

// handle scrolling to bottom
const scrollToBottom = () => {
	window.scrollTo({
		top: document.body.scrollHeight,
		behavior: "smooth",
	});
};

// Demo response (from scout api) :
/* 
[
	{
		"cas": null,
		"name": "methanol",
		"provider": "beta-static.fishersci.com",
		"verified": true,
		"filepath": "verified/methanol_beta-static.fishersci.com_3.pdf",
		"url": "https://beta-static.fishersci.com/content/dam/fishersci/en_US/documents/programs/education/regulatory-documents/sds/chemicals/chemicals-m/S25426A.pdf"
	},
]

*/