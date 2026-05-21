infrared.city SDK Hackathon

# 5 lines of code.  Any city.  Any climate.

Three days to explore what's possible when urban climate data becomes an API call. Build an app, a workflow, a reporting tool, a plugin — and win up to €5,000 in infrared.city credits.

[Join the Hackathon](https://hackathon.infrared.city/get-key) [Submit Project](https://hackathon.infrared.city/submit)

8

Analysis Types

< 1 min

per simulation

Any

city polygon

€5K

Prize

![3D city thermal simulation — San Francisco with heat-comfort overlay](https://pub-196eb52bea2944ac94bf7d6015f31748.r2.dev/media/image/7dlrnpjlip7g/optimised.jpg)

SDK · gen\_grid\_image() · San Francisco

Hackathon opens

## 27 May 2026

06

days

17

hours

20

minutes

42

seconds

Get the launch email

We'll send the API key form + Discord invite on May 27. No other emails.

Notify me

📅 Save the date: [Google](https://www.google.com/calendar/render?action=TEMPLATE&text=Infrared+SDK+Buildathon&dates=20260527T150000Z%2F20260531T220000Z&details=5+lines+of+code.+Any+city.+Any+climate.%0A%0AKickoff+Wed+May+27+17%3A00+CET+%C2%B7+Submission+deadline+Sun+May+31+24%3A00+CET+%C2%B7+Winners+Tue+Jun+2.%0A%0Ahttps%3A%2F%2Fhackathon.infrared.city&location=Online) [Outlook](https://outlook.live.com/owa/?path=%2Fcalendar%2Faction%2Fcompose&rru=addevent&subject=Infrared+SDK+Buildathon&body=5+lines+of+code.+Any+city.+Any+climate.%0A%0AKickoff+Wed+May+27+17%3A00+CET+%C2%B7+Submission+deadline+Sun+May+31+24%3A00+CET+%C2%B7+Winners+Tue+Jun+2.%0A%0Ahttps%3A%2F%2Fhackathon.infrared.city&location=Online&startdt=2026-05-27T15%3A00%3A00.000Z&enddt=2026-05-31T22%3A00%3A00.000Z) [Apple / iCal](https://hackathon.infrared.city/hackathon.ics)

Infrared SDK

## 8 analyses, one SDK

Wind, sun, daylight, sky view, thermal comfort — all from a single Python client. Try it live below — real simulation endpoints, all eight engines.

Infrared SDK Playground

Live simulation endpoints, automatic tiling for large areas, all eight engines. [Read the docs →](https://infrared.city/docs/sdk/)

Infrared Skills

## Build with your AI agents.

Drop-in skills for Claude Code, Cursor, and Codex, plus a Jupyter cookbook for every analysis. Your agents and your engineers share the same recipes — integrations that used to take a sprint now ship in an afternoon.

- →Natural language → simulation → georeferenced result
- →Works with Claude Code, Cursor, and Copilot
- →Notebooks for every analysis type

[Browse on GitHub](https://github.com/Infrared-city/infrared-skills)

![Infrared agent skills orbit — Claude, OpenAI, Cursor logos with simulation glyphs](https://pub-196eb52bea2944ac94bf7d6015f31748.r2.dev/media/image/er7xea79kb98/optimised.jpg)

6 challenges + Open

## Challenge tracks

Pick one. Or ignore them all and ship in the Open track.

![The Tree Budget simulation example](https://pub-196eb52bea2944ac94bf7d6015f31748.r2.dev/media/image/o43dfya05wkx/optimised.jpg)

### The Tree Budget

UTCI · Thermal Comfort Statistics

One million euros for canopy. Where does each tree buy back the most °C of street relief?

![The Downwash simulation example](https://pub-196eb52bea2944ac94bf7d6015f31748.r2.dev/media/image/hcam4d39t8zo/optimised.jpg)

### The Downwash

Wind Speed · Pedestrian Wind Comfort

New tower, new weather. Map what happens at the curb before the building exists.

![Daylight Banking simulation example](https://pub-196eb52bea2944ac94bf7d6015f31748.r2.dev/media/image/j0kq47vvwrzq/optimised.jpg)

### Daylight Banking

Direct Sun Hours · Daylight · Solar Radiation

Which streets keep their winter sun? Which rooftops are worth harvesting?

![Climate, Conversational simulation example](https://pub-196eb52bea2944ac94bf7d6015f31748.r2.dev/media/image/6wy0nxn7938v/optimised.jpg)

### Climate, Conversational

Voice · SDK · Open data

"Hey, is my street getting hotter?" A phone-callable agent grounded in simulation + open data.

![Live Weather — Event Operator simulation example](https://pub-196eb52bea2944ac94bf7d6015f31748.r2.dev/media/image/g2ro30lpeoib/optimised.jpg)

### Live Weather — Event Operator

Live weather · SDK · Agent

The Donauinselfest watcher. Flag the hot, windy, UV-risky hours — with maps showing where trouble lands.

![The Cool Route simulation example](https://pub-196eb52bea2944ac94bf7d6015f31748.r2.dev/media/image/f9w8515rk47d/optimised.jpg)

### The Cool Route

Satellite imagery · GIS · Routing

Pull trees and surfaces from satellite imagery, then plan the shadiest run home.

Open trackAny use of the Infrared SDK. Surprise us.

🏆 Prizes

## What you win

Credits are redeemable for any infrared.city simulation — wind, solar, thermal, daylight. Use them to keep building after the event.

1st place

€5,000

in infrared.city credits

That's ~120,000 simulations. Keep building on real urban climate data.

2nd place

€2,000

in credits

Full SDK access to take your project further after the event.

3rd place

€1,000

in credits

Plus feedback from the infrared.city team on your submission.

SDK quick-start

## 5 lines. One simulation.

Install, point at a polygon, get a numpy array back.

$ install

```
pip install infrared-sdk
```

$ run

```
from infrared_sdk import InfraredClient
from infrared_sdk.analyses.types import WindModelRequest, AnalysesName

polygon = {"type": "Polygon", "coordinates": [[[11.57, 48.19], [11.58, 48.19], [11.58, 48.20], [11.57, 48.20], [11.57, 48.19]]]}

with InfraredClient() as client:
    area = client.buildings.get_area(polygon)
    result = client.run_area_and_wait(
        WindModelRequest(analysis_type=AnalysesName.wind_speed, wind_speed=15, wind_direction=180),
        polygon, buildings=area.buildings,
    )
print(result.merged_grid)  # numpy array, m/s
```

📅 May 27–31, 2026 · Online

## Schedule

Kickoff

Wednesday · May 27

17:00–19:00 CET

Online kickoff— SDK intro, challenge prompts, team formation

Day 1

Thursday · May 28

09:00–10:00 CET

Open Q&A— Drop in, not mandatory

17:00–18:00 CET

Afternoon checkup

Day 2

Friday · May 29

09:00–10:00 CET

Open Q&A— Drop in, not mandatory

17:00–19:00 CET

Closing session— Submission walkthrough, final Q&A

Deadline

Sunday · May 31

End of day

Submission deadline— GitHub repo, demo, short description

Results

Tuesday · June 2

17:00 CET

Winner announcement— Online

Who this is for

## Built for builders

You don't need a background in urban planning. You need curiosity and a text editor.

### Developers & computational designers

Want to work with environmental simulation data and build on top of a programmable analysis layer.

### Architects & urban planners

With coding experience — looking to automate analysis that previously took days of manual setup.

### Researchers

Building tools on top of spatial climate data for academic or applied projects.

### Students & practitioners

Curious about what you can build when urban climate simulation becomes an API call.

What we provide

## Starter kit

Everything you need to go from zero to a working prototype during the event.

### Jupyter notebooks

From quickstart to error handling — one notebook per analysis type.

### Infrared SKILL.md

Drop-in agent interface. Works with Claude Code, Cursor, Copilot, Codex.

### Python scripts

Runnable examples including async, webhook, and tiling patterns.

### Gradio recipe

Ship a public demo on Hugging Face Spaces in under 30 minutes.

FAQ

## Questions

Do I need an API key?+

Yes — get one free on the [registration page](https://hackathon.infrared.city/get-key). One key per team, valid for the duration of the event.

Team size?+

1–4 people. Solo submissions are welcome. Find teammates on the [participant canvas](https://hackathon.infrared.city/participants).

What can I build?+

Anything using the Infrared SDK — web app, CLI, API, agent, notebook, visualization. Pick a challenge track or ship in the Open track. Browse the [SDK docs](https://infrared.city/docs/sdk/) for what's possible.

How are projects judged?+

Technical depth, creativity, real-world impact, and presentation. Three winners — €5,000 / €2,000 / €1,000 in cloud credits.

Where do I submit my project?+

The [submission page](https://hackathon.infrared.city/submit) opens at kickoff. Deadline is Sun May 31, 24:00 CET.

Can I use AI agents?+

Yes — that's a whole track. The [Infrared skills repo](https://github.com/Infrared-city/infrared-skills) drops into Claude Code, Cursor, and Copilot. There's also a Jupyter cookbook with one notebook per analysis.

API rate limits / cost?+

Hackathon keys are free for the duration. Each analysis runs on real compute — be reasonable; don't burn the budget on one team. After June 3 the keys auto-deactivate.

Is there a Discord / chat?+

The link will be sent in the kickoff email on May 27. Sign up on the landing page if you haven't already so you get it.

## Ready to build?

Climate simulation data is only useful if it can be acted on. Three days. Real data. Your ideas.

[Join the Buildathon](https://hackathon.infrared.city/get-key) [Find Teammates](https://hackathon.infrared.city/participants)

Kickoff · Wednesday May 27th, 17:00 CET · Online