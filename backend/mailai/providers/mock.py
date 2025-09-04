"""Mock providers for testing and development without credentials."""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import hashlib

from .interfaces import (
    GmailProvider, EmbedProvider, RerankProvider, LLMProvider, VectorStore, BM25Provider,
    MessageMeta, Message, ScoredCandidate, Citation, QueryPlan
)


class MockGmailProvider(GmailProvider):
    """Mock Gmail provider with realistic CoolSculpting Elite return data."""
    
    def __init__(self):
        self.authenticated = True
        self._fixture_messages = self._create_fixture_messages()
    
    def _create_fixture_messages(self) -> List[Message]:
        """Create realistic fixture messages for CoolSculpting Elite returns."""
        base_date = datetime(2025, 2, 1)
        
        messages = []
        
        # Thread 1: Initial return request
        messages.extend([
            Message(
                gmail_id="G-001",
                thread_id="T-001", 
                date=base_date + timedelta(days=1),
                from_email="clinic.manager@example.com",
                subject="CoolSculpting Elite Return Request - Machine Serial CS-2024-001",
                labels=["INBOX", "Returns"],
                body="""Dear Returns Team,

We need to return our CoolSculpting Elite machine (Serial: CS-2024-001) purchased in December 2024. The unit has been experiencing consistent temperature regulation issues that make it unsafe for patient treatments.

We've documented multiple instances where the machine won't process treatments without the P3 protocol, but even with P3 the cooling is erratic. Our technician reports the system shows "Error Code E-47" repeatedly.

Please advise on the RMA process and return shipping requirements.

Best regards,
Dr. Sarah Wilson
Aesthetic Wellness Clinic""",
                snippet="We need to return our CoolSculpting Elite machine (Serial: CS-2024-001)..."
            ),
            Message(
                gmail_id="G-002",
                thread_id="T-001",
                date=base_date + timedelta(days=2),
                from_email="returns@allergan.com",
                subject="RE: CoolSculpting Elite Return Request - RMA#: RMA-2025-0847",
                labels=["INBOX", "Returns"],
                body="""Dr. Wilson,

Thank you for contacting us regarding your CoolSculpting Elite unit CS-2024-001.

I've created RMA#: RMA-2025-0847 for your return. Please note:

1. Return authorization expires in 30 days
2. Machine must be returned in original packaging or equivalent protective crate
3. All accessories and documentation must be included
4. Return shipping label will be provided - DO NOT ship without approved label

The unit will be inspected upon receipt. If the issues are confirmed as manufacturing defects, you'll receive a full credit. Please note that modifications or damage not covered under warranty cannot be credited.

Next steps:
- Our logistics team will contact you within 48 hours
- LTL freight pickup will be scheduled  
- Return label and bill of lading will be emailed

RMA Specialist
Allergan Aesthetics Returns Department""",
                snippet="I've created RMA#: RMA-2025-0847 for your return..."
            )
        ])
        
        # Thread 2: Logistics coordination
        messages.extend([
            Message(
                gmail_id="G-003",
                thread_id="T-002",
                date=base_date + timedelta(days=3),
                from_email="logistics@abbvie.com",
                subject="CoolSculpting Elite Return - LTL Pickup Coordination RMA-2025-0847",
                labels=["INBOX", "Logistics"],
                body="""Dr. Wilson / Aesthetic Wellness Clinic,

This is regarding the LTL pickup for your CoolSculpting Elite return (RMA-2025-0847).

PICKUP DETAILS:
- Pickup Window: February 8-10, 2025 (8AM-5PM)
- Carrier: XYZ Logistics
- Contact: Mike Rodriguez (555) 123-4567
- Waybill#: WB-2025-3847

PACKAGING REQUIREMENTS:
- Machine must be palletized and secured
- Original crate preferred, or equivalent wooden crate
- All cables and accessories in separate box
- Documentation packet sealed in waterproof envelope

CRITICAL: The freight carrier will NOT accept the shipment if:
- Unit is not properly crated/palletized
- Weight exceeds 850 lbs total
- Dimensions exceed 48"x36"x72"
- Hazardous materials labels are missing

Your return label and bill of lading are attached. The pickup window cannot be extended without rebooking fees.

Please confirm receipt and pickup availability.

Mike Chen
AbbVie Logistics Coordinator""",
                snippet="This is regarding the LTL pickup for your CoolSculpting Elite return..."
            )
        ])
        
        # Thread 3: Packaging issues  
        messages.extend([
            Message(
                gmail_id="G-004",
                thread_id="T-003",
                date=base_date + timedelta(days=7),
                from_email="clinic.manager@example.com",
                subject="URGENT: Return Packaging Problem - RMA-2025-0847",
                labels=["INBOX", "Returns", "URGENT"],
                body="""Returns Team,

We have a critical issue with the CoolSculpting Elite return packaging for RMA-2025-0847.

Our original crate was damaged during installation and cannot be used. We've obtained a custom wooden crate (50"x38"x74") but your logistics team is saying it exceeds the size limits.

The machine cannot be safely shipped in a smaller container. We've spent $800 on this custom crate and the pickup is scheduled for tomorrow.

Two options:
1. Accept the slightly oversized crate (exceeds by 2" on height only)
2. Provide alternative packaging specifications that will actually work

This delay is costing us money and preventing us from ordering a replacement unit. Please escalate this immediately.

Dr. Sarah Wilson
(555) 987-6543""",
                snippet="We have a critical issue with the CoolSculpting Elite return packaging..."
            ),
            Message(
                gmail_id="G-005",
                thread_id="T-003",
                date=base_date + timedelta(days=7, hours=3),
                from_email="returns@allergan.com", 
                subject="RE: URGENT: Return Packaging Problem - RMA-2025-0847",
                labels=["INBOX", "Returns"],
                body="""Dr. Wilson,

I understand your frustration with the packaging requirements. Let me clarify the situation:

The 72" height limit is a hard constraint from our freight carriers. However, we can approve the 74" crate under the following conditions:

1. Additional handling fee of $150 (will be credited if return is approved)
2. Special handling label must be attached 
3. You must sign liability waiver for oversized freight

I'm attaching:
- Updated return label with "OVERSIZED" designation
- Liability waiver form (sign and return immediately)
- Special handling labels (print and affix to all 4 sides)

The pickup can proceed tomorrow if we receive the signed waiver by 5PM today.

Note: This is a one-time exception. Future returns must comply with standard size limits.

Maria Santos
Senior RMA Specialist""",
                snippet="The 72\" height limit is a hard constraint from our freight carriers..."
            )
        ])
        
        # Thread 4: Credit processing
        messages.extend([
            Message(
                gmail_id="G-006", 
                thread_id="T-004",
                date=base_date + timedelta(days=21),
                from_email="returns@allergan.com",
                subject="CoolSculpting Elite Return Processed - Credit Memo #CM-2025-1847",
                labels=["INBOX", "Credits"],
                body="""Dr. Wilson,

Your CoolSculpting Elite return (RMA-2025-0847, Serial: CS-2024-001) has been received and inspected.

INSPECTION FINDINGS:
- Confirmed: Temperature regulation failure (Error Code E-47)
- Confirmed: P3 protocol bypass issues  
- Root cause: Faulty thermal sensor array
- Classification: Manufacturing defect

APPROVED CREDIT:
- Original Purchase Price: $45,500.00
- Less: Restocking Fee: $0.00 (waived - manufacturing defect)
- Less: Return Shipping: $425.00
- Credit Amount: $45,075.00

Credit Memo #CM-2025-1847 has been issued and will appear on your next statement. Processing time is 7-10 business days.

REPLACEMENT ELIGIBILITY:
You are eligible for priority replacement at standard pricing. Your original purchase history qualifies you for:
- Extended warranty (3 years vs standard 2 years)
- Free training refresh for 2 technicians
- Priority technical support tier

Would you like me to connect you with our sales team for replacement options?

Maria Santos
Senior RMA Specialist
Allergan Aesthetics""",
                snippet="Your CoolSculpting Elite return has been received and inspected..."
            )
        ])
        
        # Thread 5: Follow-up questions
        messages.extend([
            Message(
                gmail_id="G-007",
                thread_id="T-005", 
                date=base_date + timedelta(days=25),
                from_email="clinic.manager@example.com",
                subject="CoolSculpting Elite - Replacement Unit Questions",
                labels=["INBOX"],
                body="""Hi Maria,

Thank you for processing our return so efficiently. I have a few questions about the replacement unit:

1. Is the thermal sensor issue fixed in newer production units?
2. What's the lead time for a replacement CoolSculpting Elite?  
3. Can we get the same serial number prefix (CS-2024-xxx) for our records?
4. Will the replacement come with updated P3 protocols?

Also, we're considering ordering a second unit. Would there be any volume discounting available?

Our patients have been asking when we'll have CoolSculpting available again, so timing is important for us.

Best regards,
Dr. Sarah Wilson""",
                snippet="Thank you for processing our return so efficiently..."
            ),
            Message(
                gmail_id="G-008",
                thread_id="T-005",
                date=base_date + timedelta(days=26),
                from_email="sales@allergan.com",
                subject="RE: CoolSculpting Elite - Replacement Unit Questions",
                labels=["INBOX", "Sales"],
                body="""Dr. Wilson,

Thank you for your interest in replacement equipment. Let me address your questions:

1. THERMAL SENSOR FIX: Yes, all units manufactured after January 2025 have the updated thermal sensor array (Gen 3). This completely resolves the E-47 error issue.

2. LEAD TIME: Current lead time is 6-8 weeks for CoolSculpting Elite units. However, as a return customer, we can prioritize your order for 4-5 week delivery.

3. SERIAL NUMBERS: New units use CS-2025-xxx format (reflects manufacturing year). We cannot replicate 2024 serials.

4. P3 PROTOCOLS: All new units ship with P3 v2.1, which is more robust and eliminates the bypass requirement issues you experienced.

VOLUME PRICING:
For 2+ units ordered together:
- 8% discount on second unit
- Free extended warranty on both units  
- Complimentary technician certification for up to 4 staff

I'd be happy to schedule a call to discuss your specific needs and timeline.

Best regards,
Jennifer Walsh  
Senior Sales Representative
Allergan Aesthetics
(555) 234-5678""",
                snippet="Thank you for your interest in replacement equipment..."
            )
        ])
        
        return messages
    
    async def search(self, query_str: str) -> List[MessageMeta]:
        """Mock search based on query string keywords."""
        query_lower = query_str.lower()
        
        # Simple keyword matching
        keywords = [
            'coolsculpting', 'elite', 'return', 'rma', 'ship', 'shipping',
            'label', 'freight', 'pickup', 'crate', 'packaging', 'allergan',
            'abbvie', 'credit', 'serial', 'cs-2024', 'p3', 'thermal'
        ]
        
        matched_messages = []
        for msg in self._fixture_messages:
            # Check if any keywords match in subject or body
            search_text = f"{msg.subject} {msg.body}".lower()
            if any(keyword in query_lower for keyword in keywords if keyword in search_text):
                matched_messages.append(MessageMeta(
                    gmail_id=msg.gmail_id,
                    thread_id=msg.thread_id,
                    date=msg.date,
                    from_email=msg.from_email,
                    subject=msg.subject,
                    labels=msg.labels,
                    snippet=msg.snippet
                ))
        
        return matched_messages
    
    async def fetch_bodies(self, message_ids: List[str]) -> List[Message]:
        """Fetch full messages by ID."""
        return [msg for msg in self._fixture_messages if msg.gmail_id in message_ids]
    
    async def authenticate(self) -> bool:
        """Mock authentication (always succeeds)."""
        return True


class MockEmbedProvider(EmbedProvider):
    """Mock embedding provider with deterministic outputs."""
    
    def __init__(self, dim: int = 384):
        self._dim = dim
        random.seed(42)  # Deterministic embeddings
    
    async def embed(self, texts: List[str]) -> np.ndarray:
        """Generate mock embeddings based on text hash."""
        embeddings = []
        for text in texts:
            # Create deterministic embedding from text hash
            hash_val = hashlib.md5(text.encode()).hexdigest()
            seed = int(hash_val[:8], 16)
            np.random.seed(seed)
            embedding = np.random.normal(0, 1, self._dim).astype(np.float32)
            # Normalize
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding)
        
        return np.array(embeddings)
    
    @property
    def dimension(self) -> int:
        return self._dim
    
    @property  
    def model_name(self) -> str:
        return "mock-gte-small"


class MockRerankProvider(RerankProvider):
    """Mock reranking provider."""
    
    async def rerank(
        self, 
        query: str, 
        candidates: List[ScoredCandidate]
    ) -> List[ScoredCandidate]:
        """Mock reranking based on keyword overlap."""
        query_words = set(query.lower().split())
        
        for candidate in candidates:
            text_words = set(candidate.text.lower().split())
            overlap = len(query_words & text_words)
            candidate.score = overlap / max(len(query_words), 1) + random.uniform(0, 0.1)
        
        # Sort by score and return top candidates
        candidates.sort(key=lambda x: x.score or 0, reverse=True)
        return candidates[:50]  # Return top 50
    
    @property
    def model_name(self) -> str:
        return "mock-bge-reranker"


class MockLLMProvider(LLMProvider):
    """Mock LLM provider with template-based responses."""
    
    async def summarize(
        self, 
        thread_chunks: List[str], 
        topic: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Generate mock summary with citations."""
        
        # Mock summary
        summary = f"""## Thread Summary: {topic}

Based on the email thread, here are the key findings:

• **Return Request**: CoolSculpting Elite machine experiencing temperature regulation issues and P3 protocol failures
• **RMA Process**: Return authorization RMA-2025-0847 approved with 30-day window
• **Logistics**: LTL freight pickup coordinated with special oversized packaging approval
• **Resolution**: Manufacturing defect confirmed, full credit of $45,075.00 issued
"""
        
        # Mock bullets with citations  
        bullets = [
            {
                "text": "CoolSculpting Elite machine (Serial: CS-2024-001) experiencing temperature regulation issues",
                "quote": "The unit has been experiencing consistent temperature regulation issues that make it unsafe for patient treatments",
                "gmail_id": "G-001",
                "thread_id": "T-001", 
                "date": "2025-02-01"
            },
            {
                "text": "Machine shows Error Code E-47 repeatedly and won't process without P3 protocol",
                "quote": "Our technician reports the system shows 'Error Code E-47' repeatedly",
                "gmail_id": "G-001",
                "thread_id": "T-001",
                "date": "2025-02-01"
            },
            {
                "text": "RMA-2025-0847 created with 30-day return authorization window",
                "quote": "I've created RMA#: RMA-2025-0847 for your return. Please note: Return authorization expires in 30 days",
                "gmail_id": "G-002", 
                "thread_id": "T-001",
                "date": "2025-02-02"
            },
            {
                "text": "Manufacturing defect confirmed in thermal sensor array, full credit approved",
                "quote": "Root cause: Faulty thermal sensor array. Classification: Manufacturing defect",
                "gmail_id": "G-006",
                "thread_id": "T-004", 
                "date": "2025-02-21"
            }
        ]
        
        return summary, bullets
    
    async def answer(
        self, 
        question: str, 
        evidence_chunks: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Citation], float]:
        """Generate mock answer with citations."""
        
        answer = f"""Based on the available evidence, here's what I found regarding: {question}

• The CoolSculpting Elite return was processed successfully through RMA-2025-0847
• The issue was confirmed as a manufacturing defect in the thermal sensor array  
• A full credit of $45,075.00 was issued after inspection
• Replacement units manufactured after January 2025 have the updated thermal sensor fix"""
        
        citations = [
            Citation(
                gmail_id="G-006",
                thread_id="T-004", 
                date=datetime(2025, 2, 21),
                quote="Root cause: Faulty thermal sensor array. Classification: Manufacturing defect"
            ),
            Citation(
                gmail_id="G-006",
                thread_id="T-004",
                date=datetime(2025, 2, 21), 
                quote="Credit Amount: $45,075.00"
            )
        ]
        
        confidence = 0.85
        
        return answer, citations, confidence
    
    async def plan_expansion(
        self, 
        question: str, 
        current_evidence: List[str],
        gaps: List[str]
    ) -> List[QueryPlan]:
        """Generate mock expansion plan."""
        
        plans = [
            QueryPlan(
                query_str='("CoolSculpting Elite" OR "CS-2024") AND ("return" OR "RMA") after:2024-12-01',
                rationale="Search for recent CoolSculpting Elite returns to find similar issues",
                est_hits=15
            ),
            QueryPlan(
                query_str='("thermal sensor" OR "Error Code E-47") from:allergan.com OR from:abbvie.com',
                rationale="Find technical communications about thermal sensor problems",
                est_hits=8
            )
        ]
        
        return plans
    
    @property
    def model_name(self) -> str:
        return "mock-llama3.1-8b"


class MockVectorStore(VectorStore):
    """Mock vector store using simple cosine similarity."""
    
    def __init__(self, dim: int = 384):
        self._dim = dim
        self._vectors: Optional[np.ndarray] = None
        self._ids: List[str] = []
    
    async def index(self, vectors: np.ndarray, ids: List[str]) -> None:
        """Index vectors with IDs."""
        self._vectors = vectors
        self._ids = ids
    
    async def search(
        self, 
        query_vector: np.ndarray, 
        top_k: int = 50
    ) -> List[Tuple[str, float]]:
        """Search using cosine similarity."""
        if self._vectors is None:
            return []
        
        # Compute cosine similarities
        similarities = np.dot(self._vectors, query_vector)
        
        # Get top-k results
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if idx < len(self._ids):
                results.append((self._ids[idx], float(similarities[idx])))
        
        return results
    
    async def save(self, path: str) -> None:
        """Mock save (no-op)."""
        pass
    
    async def load(self, path: str) -> None:
        """Mock load (no-op)."""
        pass
    
    @property
    def size(self) -> int:
        return len(self._ids) if self._ids else 0


class MockBM25Provider(BM25Provider):
    """Mock BM25 provider using simple TF-IDF."""
    
    def __init__(self):
        self._texts: List[str] = []
        self._ids: List[str] = []
    
    async def index(self, texts: List[str], ids: List[str]) -> None:
        """Index texts with IDs."""
        self._texts = texts
        self._ids = ids
    
    async def search(
        self, 
        query: str, 
        top_k: int = 100
    ) -> List[Tuple[str, float]]:
        """Mock BM25 search using keyword matching."""
        query_words = set(query.lower().split())
        
        results = []
        for i, text in enumerate(self._texts):
            if i < len(self._ids):
                text_words = set(text.lower().split())
                overlap = len(query_words & text_words)
                score = overlap / max(len(query_words), 1)
                
                if score > 0:
                    results.append((self._ids[i], score))
        
        # Sort by score and return top-k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]