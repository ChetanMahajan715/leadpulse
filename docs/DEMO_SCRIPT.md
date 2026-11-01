# LeadPulse Demo Video Script

**Length:** about 4 minutes. **Format:** screen recording with your voice.

Each scene tells you what to do on screen and what to say. Use the words as a guide and speak naturally. You don't need to sound perfect.

---

## Before you record

### Set up the screen

- [ ] Close any app already running on port 8501.
- [ ] **Keep private things off screen.** Do not open `.env` on camera, because it holds your real API key. Close it in VS Code if it's open, and do not show your private repo.
- [ ] Close extra browser tabs, and turn off notifications with Windows **Focus**.
- [ ] Open VS Code with the project, then open [leadpulse/config/scoring_config.yaml](../leadpulse/config/scoring_config.yaml) in a tab.
- [ ] In the VS Code terminal, start the app:
  ```powershell
  uv run streamlit run app.py
  ```
- [ ] Open **http://localhost:8501** and zoom the browser to **110%**.
- [ ] Check that the sidebar says **AI explanations: Gemini ✓**.
- [ ] In a second browser tab, open https://github.com/ChetanMahajan715/leadpulse.
- [ ] Press **F5** on the app tab so the form is empty.

### Start recording

1. Press **Win + Shift + R** to open the Windows Snipping Tool recorder.
2. Select the whole screen, and turn the **microphone on** if the toolbar offers it.
3. Click **Start**, wait 3 seconds, then begin speaking.

If the Snipping Tool doesn't record your voice, use **Win + G** (Xbox Game Bar) with the microphone on. Game Bar records one app window at a time, so you would record the browser and VS Code as separate clips.

Do a 20-second test first and play it back to check your voice is clear.

---

## Scene 1: Introduction (0:00 to 0:20)

**On screen:** the **Score a Lead** tab, with the sidebar visible.

**Say:**

> "Hi, I'm Chetan, and this is LeadPulse, my AI-based lead scoring system. Sales teams get more leads than they can follow up on, so this system scores each lead from 0 to 100 and tells the team who to call first, and why."

---

## Scene 2: The approach (0:20 to 0:45)

**On screen:** stay on the same tab. Point your mouse at the "How it works" bullets in the sidebar.

**Say:**

> "The key design decision is this: rules score, and AI explains. If you ask an LLM to rate a lead, the number can change between runs and nobody can audit it. So the score comes from a weighted rule engine with seven parameters. The AI only receives the finished result, and it explains it in plain English."

---

## Scene 3: Score the sample lead (0:45 to 1:50)

**Do:**
1. Click **Load sample lead**. All 11 fields fill in.

**Say:**

> "Here's the sample lead from the assignment: Rahul Sharma, a founder at an IT services company in Bangalore, looking for CRM software."

**Do:**
2. Click **Score lead**, then scroll down to the score cards.

**Say:**

> "The system gives 84 out of 100, classified as Hot, with 90 percent confidence. The quality assessment says this is a sales-ready lead."

**Do:**
3. Scroll to the **Score breakdown** chart.

**Say:**

> "This chart shows where every point came from. Founder gets full marks for decision authority. Buying intent gets 15 out of 25, because the lead names a product but mentions no urgency or budget."

**Do:**
4. Scroll to **Positive factors**, **Negative factors** and **Data-quality checks**.

**Say:**

> "Here are the positive and negative factors. And the system caught something important: the email is on example.com, a placeholder domain that doesn't match the company website. Each of those two flags lowers confidence by 5, which is why confidence is 90."

**Do:**
5. Scroll to **Scoring explanation**, **Recommended next action** and **AI follow-up email**.

**Say:**

> "Gemini writes this explanation and a personalised follow-up email. The next action is based on the rules: verify the contact details first, then call within 24 hours. Every output the assignment asks for is shown here."

---

## Scene 4: Consistent results (1:50 to 2:05)

**Do:**
1. Scroll to the small line under the email showing the **input hash**.
2. Press **F5**, click **Load sample lead**, click **Score lead**.
3. Scroll to the score, then the explanation.

**Say:**

> "Scoring has no randomness, so the same lead always gets the same score. The AI answer is also cached, so the explanation stays identical and there's no repeat API call."

---

## Scene 5: What-If Simulator (2:05 to 2:30)

**Do:**
1. Scroll to the bottom and click **What-If Simulator**.
2. Change **Job Title** to `Intern`, then click on an empty part of the page.

**Say:**

> "The What-If Simulator shows how the score reacts to a change. If this person were an intern instead of a founder, the score drops to 67 and the lead becomes Warm. Decision authority goes from 20 to 3. This uses the rule engine only, with no AI call, so it's instant."

---

## Scene 6: Missing data (2:30 to 2:50)

**Do:**
1. Press **F5**.
2. Type `Neha Gupta` in **Name** and `neha@nehadesigns.com` in **Email**.
3. Click **Score lead** and scroll to the score cards.

**Say:**

> "Real leads are often incomplete. Here I've entered only a name and an email. A blank field gets a neutral 30 percent of its points, so it's neither rewarded nor punished to zero. The score is 31, but confidence is 0 percent, and it says there's insufficient data to judge. So low score and unknown are never confused."

---

## Scene 7: Bulk CSV scoring (2:50 to 3:15)

**Do:**
1. Click the **Bulk Score (CSV)** tab.
2. Click the upload button and choose `data/sample_leads.csv`.

**Say:**

> "For a whole list of leads, the team can upload a CSV of up to 500 rows. A template is available to download. These 11 leads are scored and ranked straight away: 4 Hot, 3 Warm and 4 Cold."

**Do:**
3. Point your mouse at the table, then at **Download results CSV**.

**Say:**

> "Bad rows are skipped and reported, and the results can be downloaded. AI explanations run on request, one lead at a time, to save API calls."

---

## Scene 8: How scoring works (3:15 to 3:35)

**Do:**
1. Click the **How Scoring Works** tab.
2. Switch to VS Code and show the `scoring_config.yaml` tab.

**Say:**

> "All the parameters and weights are visible here, and they total 100. Buying intent carries the most at 25, then decision authority at 20. This page reads from one YAML config file, so a sales manager's change to a weight doesn't need any code changes."

---

## Scene 9: Reliability (3:35 to 3:55)

**Do:**
1. In VS Code, click the **+** in the terminal panel to open a new terminal.
2. Run this and wait for the result:
   ```powershell
   uv run pytest
   ```

**Say:**

> "Reliability was a priority. There's a guardrail: if the AI states a different score or class, its answer is thrown away and a rule-based template is used. If there's no API key or the AI fails, the app keeps working in offline mode. All 107 automated tests pass, and they never call the real AI."

---

## Scene 10: Closing (3:55 to 4:10)

**Do:**
1. Switch to the browser tab with the GitHub repo and scroll slowly down the README.

**Say:**

> "The full source code, setup steps, scoring methodology and test cases are in this repository. Rules were the right choice here because there's no historical sales data to train on. With won and lost deal data, the next step would be learning these weights with a model such as logistic regression. Thanks for watching."

**Do:** stop the recording.

---

## After you record

1. Watch it once. Check that your voice is clear and the score and class are readable. Check too that `.env` and your API key **never appear** on screen. If they do, record again, and don't upload that clip.
2. Upload to YouTube as **Unlisted**, or to Google Drive with sharing set to "Anyone with the link".
3. Open the link in a private browser window to confirm it plays without signing in.
4. Include the link in your reply to the company.

## If something goes wrong

| Problem | What to do |
|---|---|
| Sidebar shows Offline mode | Check that `.env` has your key, then restart the app |
| Explanation has an "Offline mode" note | Gemini may be busy. Say so and continue, because the score still works, or try again in a minute |
| You make a mistake while speaking | Pause and repeat the sentence, then trim it in the Clipchamp app |
| The video runs long | Skip Scene 4 and Scene 6 |
| The AI's wording differs from your script | That's expected. Read what's on screen, because only the scores must match |
