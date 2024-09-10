document.addEventListener('DOMContentLoaded', (event) => {
    console.log('DOM fully loaded and parsed');

    // File upload functionality
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('job_description');
    const fileList = document.getElementById('file-list');
    const browseButton = document.getElementById('browse-button');

    console.log('Drop area:', dropArea);
    console.log('File input:', fileInput);
    console.log('File list:', fileList);
    console.log('Browse button:', browseButton);

    if (dropArea && fileInput && browseButton) {
        console.log('All elements found');

        // ... (rest of the code remains unchanged) ...

        browseButton.addEventListener('click', (e) => {
            console.log('Browse button clicked');
            e.preventDefault();
            fileInput.click();
        });
    } else {
        console.log('Some elements are missing');
    }
});