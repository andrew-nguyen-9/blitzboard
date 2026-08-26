# 2026 context-factor evidence cards

These cards decide what is worth collecting, not what receives a projection weight. Every feature
must pass a point-in-time, walk-forward incremental-value test before promotion.

## Weather and venue

Collect forecast vintage and valid time separately: temperature, precipitation probability, wind
and gusts, humidity, roof state, surface, altitude, and forecast horizon. NFL field-goal research
found lower success with longer distance, cold, precipitation, and high wind, while turf and
altitude were associated with higher success; that supports specialized K/DST evaluation, not a
universal player adjustment. Source: [PLOS One pressure-kick study](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0214096).

Decision: eligible for historical testing by position and play type. Never replace a forecast
vintage with observed game weather when replaying a pregame decision.

## Travel, time zones, rest, and altitude

Collect distance, direction, time zones crossed, local kickoff, rest differential, international
travel, and altitude change. Older NFL evidence reported performance differences around phase
advances, while newer causal/replication work questions whether travel effects survive stronger
controls. Athlete reviews find physiological disruption but inconclusive performance effects.
Sources: [NFL time-zone study](https://pubmed.ncbi.nlm.nih.gov/8423745/), [elite-athlete travel
review](https://pubmed.ncbi.nlm.nih.gov/36287181/), [causal replication](https://academic.oup.com/aje/article/194/9/2499/8158079), and [NFL rest study](https://www.frontiersin.org/journals/behavioral-economics/articles/10.3389/frbhe.2024.1479832/full).

Decision: eligible, but interactions must be regularized and promoted only out of sample. Altitude
is both a potential physiology feature and a ball-flight feature; do not collapse them.

## Public personal/context events

Allowed categories are bereavement/family leave, legal proceedings, contract disputes/holdouts,
team discipline, major publicly reported family events, and selected public relationship or
controversy events for research only. Athlete research supports studying sleep/travel/training
stress, but no credible evidence found here establishes that divorce or breakup reporting improves
NFL fantasy prediction. Sources: [elite-athlete sleep meta-analysis](https://pubmed.ncbi.nlm.nih.gov/30217831/) and [travel review](https://pubmed.ncbi.nlm.nih.gov/36287181/).

Decision: all personal events remain `zero_weight` in prospective shadow data. Exclude protected
traits, private family details, undisclosed diagnoses, gossip, inferred mental state, and invasive
surveillance. A later promotion needs a preregistered taxonomy, sufficient sample, player fixed
effects/appropriate controls, multiple-testing correction, calibration benefit, and ethics review.

## Additional mandatory football context

Collect role/depth, snaps/routes/targets/carries, roster competition, coaching/scheme, offensive
line, opponent strength, schedule/rest/travel, market totals/props, suspensions, and discipline.
Separate availability probability from points conditional on playing. Trade reports become named
scenarios with confidence and destination-specific outputs; they never blend into the main
projection until a future policy explicitly enables it.

