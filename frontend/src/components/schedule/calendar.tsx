"use client";

import { useMemo, useRef } from "react";
import FullCalendar, { type DateSelectArg, type EventDropArg } from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";
import type { EventInput } from "@fullcalendar/core";

import type { Appointment } from "@/services/appointments";

import "@fullcalendar/core/index.css";
import "@fullcalendar/daygrid/index.css";
import "@fullcalendar/timegrid/index.css";

type ScheduleCalendarProps = {
  appointments: Appointment[];
  currentDate: Date;
  onDateChange: (date: Date) => void;
  onReschedule: (appointmentId: string, start: Date, end: Date) => Promise<void> | void;
  isLoading?: boolean;
};

export function ScheduleCalendar({
  appointments,
  currentDate,
  onDateChange,
  onReschedule,
  isLoading,
}: ScheduleCalendarProps) {
  const calendarRef = useRef<FullCalendar | null>(null);

  const events = useMemo<EventInput[]>(
    () =>
      appointments.map((appointment) => ({
        id: appointment.id,
        title: appointment.title,
        start: appointment.startTime,
        end: appointment.endTime,
        extendedProps: appointment,
      })),
    [appointments],
  );

  const handleDrop = async (info: EventDropArg) => {
    const appointmentId = info.event.id;
    const start = info.event.start;
    const end = info.event.end;

    if (!appointmentId || !start || !end) {
      info.revert();
      return;
    }

    try {
      await onReschedule(appointmentId, start, end);
    } catch (error) {
      console.error("Reschedule failed", error);
      info.revert();
    }
  };

  const handleSelect = (info: DateSelectArg) => {
    onDateChange(info.start);
  };

  return (
    <div className="relative rounded-lg border border-border/60 bg-card shadow-sm">
      {isLoading ? (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-background/60 backdrop-blur-sm">
          <span className="text-sm font-medium text-muted-foreground">Refreshing calendar…</span>
        </div>
      ) : null}
      <FullCalendar
        ref={(instance) => {
          calendarRef.current = instance;
        }}
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
        headerToolbar={{
          left: "prev,next today",
          center: "title",
          right: "dayGridMonth,timeGridWeek,timeGridDay",
        }}
        initialView="timeGridWeek"
        initialDate={currentDate}
        events={events}
        editable
        selectable
        selectMirror
        droppable={false}
        eventDrop={handleDrop}
        eventResize={handleDrop}
        select={handleSelect}
        datesSet={(arg) => onDateChange(arg.start)}
        height="auto"
        slotLabelFormat={{ hour: "numeric", minute: "2-digit" }}
        nowIndicator
        eventClassNames={() => ["bg-primary/80", "border-primary/40", "text-primary-foreground"]}
        eventDidMount={(info) => {
          info.el.setAttribute("data-event-id", info.event.id);
        }}
      />
    </div>
  );
}
