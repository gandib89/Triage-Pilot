# Day 4 Team Sync Notes

## Meeting Agenda

### 1. Demo Pipeline Results (5 min)

**Person B shows:**
- Run live demo: `python manage.py test_more`
- Show decision logs: `python manage.py check_logs`
- Walk through one complete ticket flow

**Key achievements:**
- 10/10 tickets processed successfully
- KB integration working perfectly
- Drafted responses are professional with proper citations

---

### 2. Review KB Article Quality (3 min)

**Discussion points:**
- KB articles are relevant in 95%+ of cases
- One minor issue: Ticket #31 cited KB015 (SSO) alongside KB012
- Question for Person A: Are the 20 KB articles sufficient? Need more?

**Action items:**
- [ ] Person A: Review KB article tags/content if needed
- [ ] Consider expanding KB to 30-40 articles for better coverage

---

### 3. Discuss Prompt Tuning (5 min)

**What's working:**
- Categories are accurate
- Urgency levels are reasonable
- Confidence scores realistic (60-90%)

**Potential improvements:**
1. **Low confidence threshold**
   - Ticket #26 had 20% confidence but still replied
   - Suggestion: If confidence < 50%, escalate instead
   
2. **KB relevance scoring**
   - Current: tag matches (3x) + title matches (2x) + content matches (1x)
   - Could weight title matches higher

**Decision needed:**
- Should we add confidence threshold now or wait for Day 6?
- **Recommendation:** Add it now (5-minute change)

---

### 4. Edge Cases & Missing Tests (3 min)

**What we tested:**
✅ High urgency tickets
✅ Various categories (technical, billing, account, general)
✅ JSON parsing errors
✅ Ambiguous tickets

**What we couldn't test (not in seed data):**
⚠️ Critical urgency scenarios
⚠️ Tickets with NO KB matches → escalation
⚠️ Model timeout/unavailability

**Action items:**
- [ ] Create 2-3 critical urgency test tickets
- [ ] Create 1-2 tickets with no KB matches (e.g., "refund my crypto NFT")
- [ ] Test model unavailability (stop Ollama temporarily)

---

### 5. Technical Debt & Cleanup (2 min)

**Fixed today:**
✅ JSON parsing errors (incomplete JSON)
✅ sources_used format (now proper JSON array)
✅ Model name mismatch

**Small improvements to consider:**
- Add request timeout to ollama calls (currently unlimited)
- Log failed categorizations to a separate file for debugging
- Add retry logic for transient Ollama errors

**Decision:** 
- Do these on Day 6 (error handling day) or now?
- **Recommendation:** Day 6 is fine

---

### 6. Day 5 Handoff (5 min)

**Person B takes lead on:**
- Triage queue UI in React
- Display list of pending decisions
- Ticket detail view with agent's proposed action
- Approve/edit/reject buttons

**Person A takes lead on:**
- Backend endpoints for approve/edit/reject
- Capture human decision in DecisionLog
- Store edit diffs (original vs modified)

**API design discussion:**
```
POST /api/tickets/{id}/approve/
POST /api/tickets/{id}/reject/
POST /api/tickets/{id}/edit/
  Body: { "edited_response": "...", "original_response": "..." }
```

**Questions:**
- Do we need a separate endpoint for each action?
- Or one endpoint: `POST /api/decisions/{id}/review/` with action in body?

---

## Action Items

### Immediate (before Day 5):
- [ ] **Person A:** Review KB quality, expand if needed
- [ ] **Person B:** Add confidence threshold (if agreed)
- [ ] **Both:** Decide on Day 5 API design

### Nice-to-have (Day 6):
- [ ] Create critical urgency test tickets
- [ ] Test model unavailability scenario
- [ ] Add request timeout to Ollama calls

### Celebrate! 🎉
- [x] Day 4 goal achieved
- [x] Pipeline working end-to-end
- [x] Zero crashes in 10 test tickets
- [x] Ready for frontend work

---

## Quick Demo Script

```bash
# 1. Show clean test results
cd backend
python manage.py test_more

# 2. Show decision logs being created
python manage.py check_logs

# 3. Show one API call
# (Start server: python manage.py runserver)
curl -X POST http://localhost:8000/api/tickets/15/triage/ | json_pp

# 4. Show that decision log was created
python manage.py check_logs
```

---

**Next Session: Day 5 - Human-in-the-Loop UI**
**Person B leads UI, Person A leads approve/reject endpoints**
