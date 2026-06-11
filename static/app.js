// NEXUS SYS_DECK - Cockpit Controller Script

document.addEventListener("DOMContentLoaded", () => {
    // --- State Variables ---
    let activeDocId = null;
    let pollInterval = null;
    let activeTab = "tab-summary";

    // --- DOM Elements ---
    const dashboardSection = document.getElementById("dashboard-section");
    const refreshDocsBtn = document.getElementById("refresh-docs-btn");
    const docList = document.getElementById("doc-list");
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const uploadStatus = document.getElementById("upload-status");
    const clockDisplay = document.getElementById("clock-display");

    // Metrics Display
    const metricUploaded = document.getElementById("metric-uploaded");
    const metricProcessed = document.getElementById("metric-processed");
    const metricFailed = document.getElementById("metric-failed");

    // Workspace Display States
    const noSelectionState = document.getElementById("no-selection-state");
    const activeDocumentState = document.getElementById("active-document-state");
    const selectedDocName = document.getElementById("selected-doc-name");
    const selectedDocId = document.getElementById("selected-doc-id");
    const selectedDocDate = document.getElementById("selected-doc-date");
    const selectedDocStatusBadge = document.getElementById("selected-doc-status-badge");

    // Result Outputs
    const summaryView = document.getElementById("summary-view");
    const riskView = document.getElementById("risk-view");
    const metaClass = document.getElementById("meta-class");
    const metaAuthors = document.getElementById("meta-authors");
    const metaCompanies = document.getElementById("meta-companies");
    const metaDates = document.getElementById("meta-dates");
    const metaKeywords = document.getElementById("meta-keywords");
    const resultsTabBtns = document.querySelectorAll(".results-tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    // Chat elements
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatMessages = document.getElementById("chat-messages");

    // --- Run Immersive System Clock ---
    function updateClock() {
        const now = new Date();
        const hrs = String(now.getHours()).padStart(2, '0');
        const mins = String(now.getMinutes()).padStart(2, '0');
        const secs = String(now.getSeconds()).padStart(2, '0');
        if (clockDisplay) {
            clockDisplay.innerText = `${hrs}:${mins}:${secs}`;
        }
    }
    updateClock();
    setInterval(updateClock, 1000);

    // --- Core API Helpers (Auth-Free) ---
    async function apiFetch(url, options = {}) {
        const response = await fetch(url, options);
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || `API Error: ${response.status}`);
        }
        return response;
    }

    async function fetchDocuments() {
        try {
            const response = await apiFetch("/documents");
            const docs = await response.json();
            renderDocumentList(docs);
            updateMetrics(docs);
        } catch (err) {
            console.error("Error retrieving documents archive:", err);
        }
    }

    function renderDocumentList(docs) {
        if (docs.length === 0) {
            docList.innerHTML = `<div class="doc-list-empty">NO VOLUMES DETECTED IN STORAGE.</div>`;
            return;
        }

        let html = "";
        docs.forEach(doc => {
            const isActive = doc.id === activeDocId ? "active" : "";
            const statusClass = `status-${doc.status.toLowerCase()}`;
            const formattedDate = formatDate(doc.created_at);

            html += `
                <div class="doc-item ${isActive}" data-id="${doc.id}">
                    <div class="doc-item-title" title="${doc.file_name}">${doc.file_name}</div>
                    <div class="doc-item-meta">
                        <span class="doc-item-date">${formattedDate}</span>
                        <span class="doc-item-status ${statusClass}">${doc.status}</span>
                    </div>
                </div>
            `;
        });
        docList.innerHTML = html;

        // Register Click Events
        document.querySelectorAll(".doc-item").forEach(item => {
            item.addEventListener("click", () => {
                const docId = item.getAttribute("data-id");
                selectDocument(docId, docs);
            });
        });
    }

    function updateMetrics(docs) {
        const total = docs.length;
        const processed = docs.filter(d => d.status.toLowerCase() === "processed").length;
        const failed = docs.filter(d => d.status.toLowerCase() === "failed").length;

        metricUploaded.innerText = total;
        metricProcessed.innerText = processed;
        metricFailed.innerText = failed;
    }

    // --- Document Selector ---
    async function selectDocument(docId, cachedDocsList) {
        activeDocId = docId;
        
        // Highlight active sidebar item
        document.querySelectorAll(".doc-item").forEach(item => {
            if (item.getAttribute("data-id") === docId) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        // Hide Standby Screen
        noSelectionState.classList.add("hidden");
        activeDocumentState.style.display = "flex";

        // Query fresh details
        await loadDocumentDetails(docId);
        // Clear chat history
        resetChat();
    }

    async function loadDocumentDetails(docId) {
        if (activeDocId !== docId) return;

        try {
            const response = await apiFetch(`/documents/${docId}`);
            const doc = await response.json();
            
            // Set details
            selectedDocName.innerText = doc.file_name;
            selectedDocId.innerText = doc.id;
            selectedDocDate.innerText = formatDate(doc.created_at);
            
            // Status badge
            selectedDocStatusBadge.className = `badge status-${doc.status.toLowerCase()}`;
            selectedDocStatusBadge.innerText = doc.status;

            // Fetch and Paint DAG Node Visuals
            const runsResponse = await apiFetch(`/documents/${docId}/runs`);
            const runs = await runsResponse.json();
            paintDagTimeline(doc.status, runs, doc.classification);

            // Populate Results
            populateAgentResults(doc);

        } catch (err) {
            console.error("Error retrieving document telemetry details:", err);
        }
    }

    // --- Coordinator DAG Timeline Painter ---
    function paintDagTimeline(overallStatus, runs, classification) {
        const agents = ["ingestion", "classification", "metadata", "summarization", "embedding", "risk_analysis"];
        
        // Map current run statuses
        const runMap = {};
        runs.forEach(r => {
            runMap[r.agent_name] = r;
        });

        const isRiskEligible = ["contract", "medical report", "legal document"].includes(classification);

        agents.forEach(agent => {
            const node = document.getElementById(`node-${agent}`);
            if (!node) return;

            const run = runMap[agent];
            node.className = "dag-node"; // reset classes
            const statusLabel = node.querySelector(".node-status");

            if (agent === "risk_analysis" && classification && !isRiskEligible) {
                node.classList.add("node-skipped");
                statusLabel.innerText = "SKIPPED";
                return;
            }

            if (run) {
                if (run.status === "running") {
                    node.classList.add("node-running");
                    statusLabel.innerText = "RUNNING...";
                } else if (run.status === "completed") {
                    node.classList.add("node-completed");
                    statusLabel.innerText = "COMPLETED";
                } else if (run.status === "failed") {
                    node.classList.add("node-failed");
                    statusLabel.innerText = "FAILED";
                }
            } else {
                // If the overall job is processed, but this run record is missing, it's either skipped or pending
                if (overallStatus.toLowerCase() === "processed" && agent !== "risk_analysis") {
                    node.classList.add("node-completed");
                    statusLabel.innerText = "COMPLETED";
                } else if (overallStatus.toLowerCase() === "failed") {
                    node.classList.add("node-skipped");
                    statusLabel.innerText = "ABORTED";
                } else if (overallStatus.toLowerCase() === "processing") {
                    node.classList.add("node-running");
                    statusLabel.innerText = "WAITING...";
                } else {
                    statusLabel.innerText = "PENDING";
                }
            }
        });

        // Toggle risk node visual line highlights
        const riskConnector = document.querySelector(".risk-connector");
        const riskNode = document.querySelector(".risk-node");
        if (classification && !isRiskEligible) {
            riskConnector.style.opacity = "0.2";
            riskNode.style.opacity = "0.2";
        } else {
            riskConnector.style.opacity = "1.0";
            riskNode.style.opacity = "1.0";
        }
    }

    // --- Populate Results Tab ---
    function populateAgentResults(doc) {
        // Render Summary Tab
        if (doc.summary) {
            summaryView.innerHTML = parseMarkdown(doc.summary);
        } else {
            summaryView.innerHTML = `<p class="placeholder-text">SUMMARY_AGT is compiling summaries. Readout will print when complete.</p>`;
        }

        // Render Metadata Tab
        metaClass.innerText = doc.classification ? doc.classification : "N/A";
        metaClass.className = `meta-val badge badge-${getClassificationColor(doc.classification)}`;

        if (doc.metadata) {
            const meta = typeof doc.metadata === "string" ? JSON.parse(doc.metadata) : doc.metadata;
            renderTags(metaAuthors, meta.authors, "NO_RECORDS");
            renderTags(metaCompanies, meta.companies, "NO_RECORDS");
            renderTags(metaDates, meta.dates, "NO_RECORDS");
            renderTags(metaKeywords, meta.keywords, "NO_RECORDS");
        } else {
            renderTags(metaAuthors, [], "PENDING_METADATA_EXEC");
            renderTags(metaCompanies, [], "PENDING_METADATA_EXEC");
            renderTags(metaDates, [], "PENDING_METADATA_EXEC");
            renderTags(metaKeywords, [], "PENDING_METADATA_EXEC");
        }

        // Render Risk Tab
        const isRiskEligible = ["contract", "medical report", "legal document"].includes(doc.classification);
        const riskTabBtn = document.getElementById("risk-tab-btn");

        if (classificationEligibilityCheck(doc.classification)) {
            riskTabBtn.style.display = "block";
            if (doc.risk_analysis) {
                riskView.innerHTML = parseMarkdown(doc.risk_analysis);
            } else {
                riskView.innerHTML = `<p class="placeholder-text">RISK_ANAL_AGT is auditing compliance factors. Results will print when complete.</p>`;
            }
        } else {
            if (doc.classification) {
                riskTabBtn.style.display = "none";
                if (activeTab === "tab-risk") {
                    document.querySelector("[data-tab='tab-summary']").click();
                }
            } else {
                riskTabBtn.style.display = "block";
                riskView.innerHTML = `<p class="placeholder-text">Inferring document classification to determine risk audit eligibility...</p>`;
            }
        }
    }

    function classificationEligibilityCheck(cls) {
        return ["contract", "medical report", "legal document"].includes(cls);
    }

    function renderTags(container, tagsList, emptyMessage) {
        if (!tagsList || tagsList.length === 0) {
            container.innerHTML = `<span class="no-tags">${emptyMessage}</span>`;
            return;
        }
        container.innerHTML = tagsList.map(tag => `<span>${tag}</span>`).join("");
    }

    function getClassificationColor(cls) {
        const colors = {
            "contract": "purple",
            "invoice": "cyan",
            "research paper": "indigo",
            "resume": "green",
            "medical report": "yellow",
            "legal document": "red",
            "other": "purple"
        };
        return colors[cls] || "purple";
    }

    // --- Drag & Drop Document Ingestion ---
    dropZone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    ["dragleave", "dragend"].forEach(type => {
        dropZone.addEventListener(type, () => {
            dropZone.classList.remove("dragover");
        });
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    async function handleFileUpload(file) {
        uploadStatus.className = "upload-status uploading";
        uploadStatus.innerText = "INGESTING VOLUME INTO STORAGE ARCHIVE...";

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch("/documents", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.detail || "Ingestion pipeline upload failure.");
            }

            const data = await response.json();
            uploadStatus.className = "upload-status success";
            uploadStatus.innerText = "INGESTION SUCCESSFUL. ANALYSIS JOB REGISTERED.";
            
            // Refresh documents list
            await fetchDocuments();
            // Automatically select new document
            selectDocument(data.document_id);
            
            // Clear status message
            setTimeout(() => { uploadStatus.innerText = ""; }, 3000);

        } catch (err) {
            uploadStatus.className = "upload-status error";
            uploadStatus.innerText = err.message;
        }
    }

    refreshDocsBtn.addEventListener("click", fetchDocuments);

    // --- RAG Chat Assistant Module ---
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!activeDocId) return;

        const question = chatInput.value.trim();
        if (!question) return;

        // Render User message
        appendChatMessage("user", question);
        chatInput.value = "";

        // Show typing indicator
        const typingBubble = appendChatMessage("assistant", "SYS // QUERYING VECTOR INDEX RECORDS...", true);

        try {
            const response = await fetch(`/documents/${activeDocId}/ask`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Query execution failed");
            }

            typingBubble.remove();
            appendChatMessage("assistant", data.answer);
        } catch (err) {
            typingBubble.remove();
            appendChatMessage("assistant", `SYS_ERR // ${err.message}`);
        }
    });

    function appendChatMessage(sender, text, isTyping = false) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${sender}-message`;
        if (isTyping) msgDiv.classList.add("typing-indicator");
        
        msgDiv.innerHTML = `<div class="message-bubble">${text}</div>`;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return msgDiv;
    }

    function resetChat() {
        chatMessages.innerHTML = `
            <div class="message assistant-message">
                <div class="message-bubble">
                    SYS // RAG vector storage connection verified. Awaiting query commands...
                </div>
            </div>
        `;
    }

    // --- Sub-navigation Tabs Event Listeners ---
    resultsTabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            activeTab = targetTab;

            resultsTabBtns.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));

            btn.classList.add("active");
            document.getElementById(targetTab).classList.add("active");
        });
    });

    // --- Utility Functions ---
    function formatDate(isoStr) {
        if (!isoStr) return "...";
        try {
            const date = new Date(isoStr);
            return date.toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            });
        } catch {
            return isoStr;
        }
    }

    function parseMarkdown(text) {
        if (!text) return "";
        let html = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        html = html.replace(/^### (.*?)$/gm, "<h3>$1</h3>");
        html = html.replace(/^## (.*?)$/gm, "<h3>$1</h3>");
        html = html.replace(/^# (.*?)$/gm, "<h3>$1</h3>");
        
        html = html.replace(/^\s*[-*+]\s+(.*?)$/gm, "<li>$1</li>");
        html = html.replace(/(<li>.*?<\/li>)+/g, "<ul>$&</ul>");
        
        html = html.replace(/\n\n/g, "</p><p>");
        html = html.replace(/\n/g, "<br>");
        
        return `<p>${html}</p>`.replace(/<p><\/p>/g, "").replace(/<p><h3>/g, "<h3>").replace(/<\/h3><\/p>/g, "</h3>");
    }

    // --- Initialize Dashboard Directly ---
    fetchDocuments();
    pollInterval = setInterval(fetchDocuments, 3000);
});
