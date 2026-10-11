// CleanHour outdoor-activity rules. Every proposed outdoor slot is checked against these
// before it reaches the timetable; the LLM never decides whether children go outside.
// context.pm25 is the forecast PM2.5 (µg/m³, rounded) for that slot.

@id("grap4_all_outdoor")
forbid(principal, action == Action::"ScheduleOutdoor", resource)
when { context.grap_stage >= 4 };

@id("grap3_outdoor_sports")
forbid(principal, action == Action::"ScheduleOutdoor", resource)
when { context.grap_stage >= 3 && resource.exertion == "high" };

@id("severe_air")
forbid(principal, action == Action::"ScheduleOutdoor", resource)
when { context.pm25 > 250 };

@id("very_poor_exertion")
forbid(principal, action == Action::"ScheduleOutdoor", resource)
when { context.pm25 > 120 && resource.exertion != "low" };

@id("very_poor_primary")
forbid(principal in Group::"primary", action == Action::"ScheduleOutdoor", resource)
when { context.pm25 > 120 };

@id("poor_morning_assembly")
forbid(principal, action == Action::"ScheduleOutdoor", resource)
when { context.pm25 > 90 && resource.kind == "assembly" };

@id("poor_asthma_watch")
forbid(principal in Group::"asthma_watch", action == Action::"ScheduleOutdoor", resource)
when { context.pm25 > 90 };

@id("default_allow")
permit(principal, action == Action::"ScheduleOutdoor", resource);
