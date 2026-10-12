"""Loads a fictional demo learner (L-DEMO). Older entries are already teacher-approved;
the two newest are pending so you can watch the propose -> approve flow."""
import time, core
D = [("Gr4-T1","Mathematics","quiz",72,"","Fractions test"),("Gr4-T2","Mathematics","quiz",78,"Thinking","Word problems; found a shortcut unprompted"),
("Gr5-T1","Mathematics","project",85,"Communication","Explained fractions to a classmate with bottle tops"),
("Gr4-T2","Science","quiz",70,"","Plants unit"),("Gr5-T2","Science","project",82,"Research","Water filter model; asked own follow-up questions"),
("Gr4-T1","English","quiz",52,"","Comprehension"),("Gr5-T1","English","quiz",48,"","Composition"),("Gr6-T1","English","quiz",50,"","Comprehension; absent 3 days that week"),
("Gr4-T3","Kiswahili","quiz",74,"","Insha"),("Gr5-T3","Kiswahili","quiz",76,"Communication","Oral presentation confident"),
("Gr5-T2","Creative Arts","teacher_note",None,"Self-management","Stays on task for long stretches when making models"),
("Gr6-T1","Mathematics","quiz",88,"","Geometry"),          # pending
("Gr6-T2","Science","quiz",86,"Thinking","Forces")]          # pending
c = core.conn()
with c:
    c.execute("DELETE FROM evidence WHERE learner='L-DEMO'"); c.execute("DELETE FROM proposals WHERE learner='L-DEMO'")
    for i, (t, s, k, sc, atl, n) in enumerate(D):
        c.execute("INSERT INTO evidence(learner,term,subject,kind,score,atl,note,teacher,status,created) VALUES(?,?,?,?,?,?,?,?,?,?)",
                  ("L-DEMO", t, s, k, sc, atl, n, "Demo Teacher", "pending" if i >= len(D) - 2 else "approved", time.time()))
print(f"Seeded L-DEMO: {len(D)-2} approved, 2 pending.")
