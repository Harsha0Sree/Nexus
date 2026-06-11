// NEXUS Front-End Application Logic

document.addEventListener("DOMContentLoaded", () => {
    // --- State Variables ---
    let token = localStorage.getItem("nexus_token");
    let userEmail = localStorage.getItem("nexus_email");
    let activeDocId = null;
    let pollInterval = null;
    let activeTab = "tab-summary";

    // --- DOM Elements ---
    const authSection = document.getElementById("auth-section");
    const dashboardSection = document.getElementById("dashboard-section");
    const authForm = document.getElementById("auth-form");
    const authEmailInput = document.getElementById("auth-email");
    const authPasswordInput = document.getElementById("auth-password");
    const authSubmitBtn = document.getElementById("auth-submit-btn");
    const authMessage = document.getElementById("auth-message");
    const tabLoginBtn = document.getElementById("tab-login-btn");
    const tabRegisterBtn = document.getElementById("tab-register-btn");

    const userEmailDisplay = document.getElementById("user-email-display");
    const logoutBtn = document.getElementById("logout-btn");
    const refreshDocsBtn = document.getElementById("refresh-docs-btn");
    const docList = document.getElementById("doc-list");
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const uploadStatus = document.getElementById("upload-status");

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

    // --- Authentication Actions ---
    let isRegisterMode = false;

    tabLoginBtn.addEventListener("click", () => {
        isRegisterMode = false;
        tabLoginBtn.classList.add("active");
        tabRegisterBtn.classList.remove("active");
        authSubmitBtn.innerText = "Sign In";
        authMessage.innerText = "";
    });

    tabRegisterBtn.addEventListener("click", () => {
        isRegisterMode = true;
        tabRegisterBtn.classList.add("active");
        tabLoginBtn.classList.remove("active");
        authSubmitBtn.innerText = "Create Account";
        authMessage.innerText = "";
    });

    authForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        authMessage.innerText = "";
        
        const email = authEmailInput.value;
        const password = authPasswordInput.value;
        const url = isRegisterMode ? "/register" : "/login";

        try {
            authSubmitBtn.disabled = true;
            authSubmitBtn.innerText = isRegisterMode ? "Registering..." : "Signing In...";
            
            const response = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Authentication failed");
            }

            if (isRegisterMode) {
                authMessage.className = "auth-message success";
                authMessage.innerText = "Registration complete! You can sign in now.";
                // Switch back to login mode automatically
                setTimeout(() => tabLoginBtn.click(), 1500);
            } else {
                // Login Mode
                token = data.access_token;
                userEmail = email;
                localStorage.setItem("nexus_token", token);
                localStorage.setItem("nexus_email", userEmail);
                showDashboard();
            }
        } catch (err) {
            authMessage.className = "auth-message error";
            authMessage.innerText = err.message;
        } finally {
            authSubmitBtn.disabled = false;
            authSubmitBtn.innerText = isRegisterMode ? "Create Account" : "Sign In";
        }
    });

    logoutBtn.addEventListener("click", () => {
        localStorage.removeItem("nexus_token");
        localStorage.removeItem("nexus_email");
        token = null;
        userEmail = null;
        activeDocId = null;
        clearInterval(pollInterval);
        showAuth();
    });

    // --- Switch Section States ---
    function showAuth() {
        authSection.classList.add("active");
        dashboardSection.classList.remove("active");
    }

    function showDashboard() {
        authSection.classList.remove("active");
        dashboardSection.classList.add("active");
        userEmailDisplay.innerText = userEmail;
        fetchDocuments();
        // Start polling documents list
        clearInterval(pollInterval);
        pollInterval = setInterval(fetchDocuments, 4000);
    }

    // --- Documents Dashboard Ingestion & Management ---
    async defFetch(url, options = {}) {
        if (!options.headers) options.headers = {};
        options.headers["Authorization"] = `Bearer ${token}`;
        
        const response = await fetch(url, options);
        if (response.status === 401) {
            // Force logout on token expiry
            logoutBtn.click();
            throw new Error("Session expired. Please log in again.");
        }
        return response;
    }

    async function fetchDocuments() {
        try {
            const response = await defFetch("/documents");
            const docs = await response.json();
            renderDocumentList(docs);
            updateMetrics(docs);
        } catch (err) {
            console.error("Error retrieving documents:", err);
        }
    }

    function renderDocumentList(docs) {
        if (docs.length === 0) {
            docList.innerHTML = `<div class="doc-list-empty">No documents uploaded yet.</div>`;
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

    // --- Document Viewer Module ---
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

        // Hide Empty State
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
            const response = await defFetch(`/documents/${docId}`);
            const doc = await response.json();
            
            // Set basic details
            selectedDocName.innerText = doc.file_name;
            selectedDocId.innerText = doc.id;
            selectedDocDate.innerText = formatDate(doc.created_at);
            
            // Status badge class
            selectedDocStatusBadge.className = `badge status-${doc.status.toLowerCase()}`;
            selectedDocStatusBadge.innerText = doc.status;

            // Fetch and Paint DAG Node Visuals
            const runsResponse = await defFetch(`/documents/${docId}/runs`);
            const runs = await runsResponse.json();
            paintDagTimeline(doc.status, runs, doc.classification);

            // Populate Results
            populateAgentResults(doc);

        } catch (err) {
            console.error("Error retrieving document details:", err);
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
                statusLabel.innerText = "Skipped";
                return;
            }

            if (run) {
                if (run.status === "running") {
                    node.classList.add("node-running");
                    statusLabel.innerText = "Running...";
                } else if (run.status === "completed") {
                    node.classList.add("node-completed");
                    statusLabel.innerText = "Completed";
                } else if (run.status === "failed") {
                    node.classList.add("node-failed");
                    statusLabel.innerText = `Failed (Attempts: ${run.retries + 1})`;
                }
            } else {
                // If the overall job is processed, but this run record is missing, it's either skipped or pending
                if (overallStatus.toLowerCase() === "processed" && agent !== "risk_analysis") {
                    node.classList.add("node-completed");
                    statusLabel.innerText = "Completed";
                } else if (overallStatus.toLowerCase() === "failed") {
                    node.classList.add("node-skipped");
                    statusLabel.innerText = "Aborted";
                } else if (overallStatus.toLowerCase() === "processing") {
                    node.classList.add("node-running");
                    statusLabel.innerText = "Waiting...";
                } else {
                    statusLabel.innerText = "Pending";
                }
            }
        });

        // Toggle risk node visual line highlights
        const riskConnector = document.querySelector(".risk-connector");
        const riskNode = document.querySelector(".risk-node");
        if (classification && !isRiskEligible) {
            riskConnector.style.opacity = "0.3";
            riskNode.style.opacity = "0.3";
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
            summaryView.innerHTML = `<p class="placeholder-text">Summarization Agent is working. Results will appear when complete.</p>`;
        }

        // Render Metadata Tab
        metaClass.innerText = doc.classification ? doc.classification : "N/A";
        metaClass.className = `meta-val badge badge-${getClassificationColor(doc.classification)}`;

        if (doc.metadata) {
            const meta = typeof doc.metadata === "string" ? JSON.parse(doc.metadata) : doc.metadata;
            renderTags(metaAuthors, meta.authors, "No authors detected");
            renderTags(metaCompanies, meta.companies, "No companies detected");
            renderTags(metaDates, meta.dates, "No dates detected");
            renderTags(metaKeywords, meta.keywords, "No keywords detected");
        } else {
            renderTags(metaAuthors, [], "Pending metadata agent execution");
            renderTags(metaCompanies, [], "Pending metadata agent execution");
            renderTags(metaDates, [], "Pending metadata agent execution");
            renderTags(metaKeywords, [], "Pending metadata agent execution");
        }

        // Render Risk Tab
        const isRiskEligible = ["contract", "medical report", "legal document"].includes(doc.classification);
        const riskTabBtn = document.getElementById("risk-tab-btn");

        if (classificationEligibilityCheck(doc.classification)) {
            riskTabBtn.style.display = "block";
            if (doc.risk_analysis) {
                riskView.innerHTML = parseMarkdown(doc.risk_analysis);
            } else {
                riskView.innerHTML = `<p class="placeholder-text">Risk Analysis Agent is evaluating compliance. Results will appear when complete.</p>`;
            }
        } else {
            // Hide or disable risk tab for invoices/resumes etc.
            if (doc.classification) {
                riskTabBtn.style.display = "none";
                // If active tab was risk, click summary instead
                if (activeTab === "tab-risk") {
                    document.querySelector("[data-tab='tab-summary']").click();
                }
            } else {
                riskTabBtn.style.display = "block";
                riskView.innerHTML = `<p class="placeholder-text">Evaluating file classification to determine risk audit eligibility...</p>`;
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

    // Drag-over styling
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
        uploadStatus.innerText = "Ingesting file into storage...";

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch("/documents", {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` },
                body: formData
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Upload failed");
            }

            uploadStatus.className = "upload-status success";
            uploadStatus.innerText = "Ingestion succeeded! Job queued.";
            
            // Refresh documents list
            await fetchDocuments();
            // Automatically select new document
            selectDocument(data.document_id);
            
            // Clear status message after 3 seconds
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
        const typingBubble = appendChatMessage("assistant", "Searching vector records and answering question...", true);

        try {
            const response = await defFetch(`/documents/${activeDocId}/ask`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Query failed");
            }

            // Remove typing bubble and print response
            typingBubble.remove();
            appendChatMessage("assistant", data.answer);
        } catch (err) {
            typingBubble.remove();
            appendChatMessage("assistant", `Error: ${err.message}`);
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
                    Hi! I have indexed this document chunks. You can ask me questions about it, and I will search the vector records to retrieve the answers.
                </div>
            </div>
        `;
    }

    // --- Sub-navigation Tabs Event Listeners ---
    resultsTabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            activeTab = targetTab;

            // Remove active states
            resultsTabBtns.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));

            // Set active states
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

    // Minimal markdown translator to avoid extra script weight
    function parseMarkdown(text) {
        if (!text) return "";
        let html = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Format headers: ### Title
        html = html.replace(/^### (.*?)$/gm, "<h3>$1</h3>");
        html = html.replace(/^## (.*?)$/gm, "<h3>$1</h3>");
        html = html.replace(/^# (.*?)$/gm, "<h3>$1</h3>");
        
        // Format bullet points: - item
        html = html.replace(/^\s*[-*+]\s+(.*?)$/gm, "<li>$1</li>");
        
        // Wrap consecutive list items in <ul> tags
        html = html.replace(/(<li>.*?<\/li>)+/g, "<ul>$&</ul>");
        
        // Paragraph splits (double newlines)
        html = html.replace(/\n\n/g, "</p><p>");
        
        // Simple carriage return mapping
        html = html.replace(/\n/g, "<br>");
        
        // Re-wrap paragraphs
        return `<p>${html}</p>`.replace(/<p><\/p>/g, "").replace(/<p><h3>/g, "<h3>").replace(/<\/h3><\/p>/g, "</h3>");
    }

    // --- App Init Check ---
    if (token) {
        showDashboard();
    } else {
        showAuth();
    }
});
