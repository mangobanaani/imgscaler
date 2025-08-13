// Import API client helpers
import { createJob, getJobStatus, getJobResultUrl } from './jobClient.js';

document.addEventListener('DOMContentLoaded', () => {
	console.log('app.js loaded');

	const uploadArea = document.getElementById('uploadArea');
	const fileInput = document.getElementById('fileInput');
	const processBtn = document.getElementById('processBtn');
	const statusDiv = document.getElementById('status');
	const progressBar = document.getElementById('progressBar');
	const progressBarInner = progressBar ? progressBar.querySelector('.progress-bar') : null;
	const originalPreview = document.getElementById('originalPreview');
	const originalPlaceholder = document.getElementById('originalPlaceholder');
	const enhancedPreview = document.getElementById('enhancedPreview');
	const enhancedPlaceholder = document.getElementById('enhancedPlaceholder');
	const originalInfo = document.getElementById('originalInfo');
	const enhancedInfo = document.getElementById('enhancedInfo');
	const saveBtn = document.getElementById('saveBtn');
	const zoomBtn = document.getElementById('zoomBtn');

	let selectedFile = null;
	let jobId = null;


		// Ensure handleFile is defined before event listeners
		function handleFile(file) {
			selectedFile = file;
			const reader = new FileReader();
			reader.onload = (e) => {
				originalPreview.src = e.target.result;
				originalPreview.classList.remove('hidden');
				originalPlaceholder.classList.add('hidden');
				// Update original image info on load
				originalPreview.onload = () => {
					if (originalInfo) {
						originalInfo.textContent = `${originalPreview.naturalWidth} × ${originalPreview.naturalHeight}px`;
						originalInfo.classList.remove('hidden');
					}
				};
			};
			reader.readAsDataURL(file);
			processBtn.disabled = false;
			statusDiv.textContent = 'Ready to enhance your image';
		}

		// Drag & Drop
		uploadArea.addEventListener('dragover', (e) => {
			console.log('dragover event');
			e.preventDefault();
			uploadArea.classList.add('dragover');
		});
		uploadArea.addEventListener('dragleave', (e) => {
			console.log('dragleave event');
			e.preventDefault();
			uploadArea.classList.remove('dragover');
		});
		uploadArea.addEventListener('drop', (e) => {
			console.log('drop event', e.dataTransfer.files);
			e.preventDefault();
			uploadArea.classList.remove('dragover');
			if (e.dataTransfer.files && e.dataTransfer.files[0]) {
				handleFile(e.dataTransfer.files[0]);
			}
		});
		uploadArea.addEventListener('click', () => {
			console.log('uploadArea clicked');
			fileInput.click();
		});
		fileInput.addEventListener('change', (e) => {
			console.log('fileInput change', e.target.files);
			if (e.target.files && e.target.files[0]) {
				handleFile(e.target.files[0]);
			}
		});

	processBtn.addEventListener('click', async () => {
		if (!selectedFile) return;
		processBtn.disabled = true;
		statusDiv.textContent = 'Uploading image...';
		progressBar.classList.remove('hidden');
		if (progressBarInner) progressBarInner.style.width = '10%';

		// Get settings
		const factor = document.getElementById('factor').value;
		const denoise = document.getElementById('denoise').checked;
		const useTFHub = document.getElementById('aiModel').value === 'tfhub';

			try {
				const job = await createJob(selectedFile, factor, denoise, useTFHub);
				console.log('Job creation response:', job);
				// Try to extract jobId from possible keys
				jobId = job.id || job.jobId || job.job_id;
				if (!jobId) {
					statusDiv.textContent = 'Error: Could not get job ID from response';
					processBtn.disabled = false;
					progressBar.classList.add('hidden');
					return;
				}
				statusDiv.textContent = 'Processing...';
				if (progressBarInner) progressBarInner.style.width = '30%';
				pollJob(jobId);
			} catch (err) {
				statusDiv.textContent = 'Error: ' + err.message;
				processBtn.disabled = false;
				progressBar.classList.add('hidden');
			}
	});

	async function pollJob(jobId) {
		let done = false;
		let progress = 30;
		while (!done) {
			await new Promise((r) => setTimeout(r, 1200));
			try {
				const status = await getJobStatus(jobId);
				if (status.status === 'done') {
					done = true;
					statusDiv.textContent = 'Download enhanced image...';
					if (progressBarInner) progressBarInner.style.width = '100%';
					showEnhanced(jobId);
				} else if (status.status === 'error') {
					statusDiv.textContent = 'Error: ' + (status.error || 'Unknown');
					processBtn.disabled = false;
					progressBar.classList.add('hidden');
					return;
				} else {
					statusDiv.textContent = 'Processing...';
					progress = Math.min(progress + 10, 90);
					if (progressBarInner) progressBarInner.style.width = progress + '%';
				}
			} catch (err) {
				statusDiv.textContent = 'Error: ' + err.message;
				processBtn.disabled = false;
				progressBar.classList.add('hidden');
				return;
			}
		}
	}

	function showEnhanced(jobId) {
		const url = getJobResultUrl(jobId);
		// Update enhanced preview
		enhancedPreview.src = url;
		enhancedPreview.classList.remove('hidden');
		enhancedPlaceholder.classList.add('hidden');

		// Update split comparison
		const splitComparison = document.getElementById('splitComparison');
		const splitOriginal = document.getElementById('splitOriginal');
		const splitEnhanced = document.getElementById('splitEnhanced');
		const splitRange = document.getElementById('splitRange');
		if (splitComparison && splitOriginal && splitEnhanced) {
			splitOriginal.src = originalPreview.src;
			splitEnhanced.src = url;
			splitComparison.classList.remove('hidden');
			// Initialize range and clip (Original left, Enhanced right)
			if (splitRange) {
				splitRange.value = 50;
				splitEnhanced.style.clipPath = `inset(0 0 0 ${splitRange.value}%)`;
				splitRange.oninput = () => {
					splitEnhanced.style.clipPath = `inset(0 0 0 ${splitRange.value}%)`;
				};
			}
		}

		// Update enhanced image info on load
		enhancedPreview.onload = () => {
			if (enhancedInfo) {
				enhancedInfo.textContent = `${enhancedPreview.naturalWidth} × ${enhancedPreview.naturalHeight}px`;
				enhancedInfo.classList.remove('hidden');
			}
		};

		// Enable save and zoom buttons
		if (saveBtn) {
			saveBtn.classList.remove('hidden');
			saveBtn.onclick = () => {
				const a = document.createElement('a');
				a.href = url;
				a.download = 'enhanced.png';
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
			};
		}
		if (zoomBtn) {
			zoomBtn.classList.remove('hidden');
			zoomBtn.onclick = () => openImageModal(url, 'Enhanced Image');
		}
	}

	// Minimal modal logic
	function openImageModal(imgUrl, title = 'Image') {
		const modal = document.getElementById('imageModal');
		const modalImg = document.getElementById('modalImage');
		const closeBtn = document.querySelector('#imageModal .close');
		const infoEl = document.getElementById('modalImageInfo');
		if (!modal || !modalImg) return;
		modalImg.src = imgUrl;
		if (infoEl) infoEl.textContent = title;
		modal.style.display = 'block';

		function hide() {
			modal.style.display = 'none';
			modalImg.classList.remove('zoomed');
			document.removeEventListener('keydown', onKey);
			modal.removeEventListener('click', onBackdrop);
			if (closeBtn) closeBtn.removeEventListener('click', hide);
			modalImg.removeEventListener('click', toggleZoom);
		}

		function onKey(e) { if (e.key === 'Escape') hide(); }
		function onBackdrop(e) { if (e.target === modal) hide(); }
		function toggleZoom() { modalImg.classList.toggle('zoomed'); }

		document.addEventListener('keydown', onKey);
		modal.addEventListener('click', onBackdrop);
		if (closeBtn) closeBtn.addEventListener('click', hide);
		modalImg.addEventListener('click', toggleZoom);
	}

	// Modal logic, split comparison, and other code...
	// ...existing code...
});
