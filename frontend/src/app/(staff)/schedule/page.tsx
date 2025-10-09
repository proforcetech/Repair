"use client";

import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { format } from "date-fns";

import { AppointmentsTable } from "@/components/schedule/appointments-table";
import {
  BookingForms,
  type PublicBookingValues,
  type StaffBookingValues,
} from "@/components/schedule/booking-forms";
import { ScheduleCalendar } from "@/components/schedule/calendar";
import { useAppointmentsSocket } from "@/hooks/use-appointments-socket";
import { fetchBays } from "@/services/bays";
import {
  autoScheduleAppointment,
  bookAppointment,
  createAppointment,
  fetchAppointments,
  fetchCalendarAppointments,
  rescheduleAppointment,
  sendAppointmentReminder,
  syncAppointmentToCalendar,
  updateAppointmentAssignment,
  type Appointment,
} from "@/services/appointments";
import { fetchTechnicians } from "@/services/dashboard";
import { showToast } from "@/stores/toast-store";

const listQueryKey = ["appointments", "list"] as const;

function toIso(datetime: string) {
  return datetime ? new Date(datetime).toISOString() : "";
}

export default function StaffSchedulePage() {
  const queryClient = useQueryClient();
  const [selectedTechnician, setSelectedTechnician] = useState<string>("");
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [autoVehicleId, setAutoVehicleId] = useState("");
  const [autoDuration, setAutoDuration] = useState(60);
  const [remindersInFlight, setRemindersInFlight] = useState<Set<string>>(new Set());
  const [syncInFlight, setSyncInFlight] = useState<Set<string>>(new Set());

  const dayFilter = useMemo(() => format(selectedDate, "yyyy-MM-dd"), [selectedDate]);
  const calendarQueryKey = useMemo(
    () =>
      [
        "appointments",
        "calendar",
        { technicianId: selectedTechnician || null, day: dayFilter },
      ] as const,
    [selectedTechnician, dayFilter],
  );

  const appointmentsQuery = useQuery({
    queryKey: listQueryKey,
    queryFn: fetchAppointments,
  });

  const calendarQuery = useQuery({
    queryKey: calendarQueryKey,
    queryFn: () =>
      fetchCalendarAppointments({
        technicianId: selectedTechnician || undefined,
        day: dayFilter,
      }),
  });

  const techniciansQuery = useQuery({
    queryKey: ["technicians", "list"],
    queryFn: fetchTechnicians,
  });

  const baysQuery = useQuery({
    queryKey: ["bays", "list"],
    queryFn: fetchBays,
  });

  const upsertAppointment = (appointment: Appointment) => {
    queryClient.setQueryData<Appointment[] | undefined>(listQueryKey, (previous) => {
      const current = previous ? [...previous] : [];
      const index = current.findIndex((item) => item.id === appointment.id);
      if (index >= 0) {
        current[index] = { ...current[index], ...appointment };
      } else {
        current.push(appointment);
      }
      return current;
    });

    queryClient.setQueryData<Appointment[] | undefined>(calendarQueryKey, (previous) => {
      if (!previous) return previous;
      const next = [...previous];
      const index = next.findIndex((item) => item.id === appointment.id);
      if (index >= 0) {
        next[index] = { ...next[index], ...appointment };
        return next;
      }
      if (
        (selectedTechnician && appointment.technicianId !== selectedTechnician) ||
        format(new Date(appointment.startTime), "yyyy-MM-dd") !== dayFilter
      ) {
        return previous;
      }
      next.push(appointment);
      return next;
    });
  };

  const removeAppointment = (appointmentId: string) => {
    queryClient.setQueryData<Appointment[] | undefined>(listQueryKey, (previous) => {
      if (!previous) return previous;
      return previous.filter((item) => item.id !== appointmentId);
    });
    queryClient.setQueryData<Appointment[] | undefined>(calendarQueryKey, (previous) => {
      if (!previous) return previous;
      return previous.filter((item) => item.id !== appointmentId);
    });
  };

  const reminderMutation = useMutation({
    mutationFn: sendAppointmentReminder,
    onMutate: async (appointmentId: string) => {
      setRemindersInFlight((current) => new Set(current).add(appointmentId));
      return appointmentId;
    },
    onSuccess: () => {
      showToast({
        title: "Reminder sent",
        description: "The customer has been notified about their appointment.",
        variant: "success",
      });
    },
    onError: (error, appointmentId) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message)
          : "Unable to send reminder.";
      showToast({
        title: "Reminder failed",
        description: message,
        variant: "destructive",
      });
      if (appointmentId) {
        setRemindersInFlight((current) => {
          const next = new Set(current);
          next.delete(appointmentId);
          return next;
        });
      }
    },
    onSettled: (_result, _error, appointmentId) => {
      if (appointmentId) {
        setRemindersInFlight((current) => {
          const next = new Set(current);
          next.delete(appointmentId);
          return next;
        });
      }
    },
  });

  const syncMutation = useMutation({
    mutationFn: syncAppointmentToCalendar,
    onMutate: async (appointmentId: string) => {
      setSyncInFlight((current) => new Set(current).add(appointmentId));
      return appointmentId;
    },
    onSuccess: () => {
      showToast({
        title: "Sync queued",
        description: "Calendar sync has been triggered for the appointment.",
        variant: "success",
      });
    },
    onError: (error, appointmentId) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message)
          : "Unable to sync appointment.";
      showToast({
        title: "Sync failed",
        description: message,
        variant: "destructive",
      });
      if (appointmentId) {
        setSyncInFlight((current) => {
          const next = new Set(current);
          next.delete(appointmentId);
          return next;
        });
      }
    },
    onSettled: (_result, _error, appointmentId) => {
      if (appointmentId) {
        setSyncInFlight((current) => {
          const next = new Set(current);
          next.delete(appointmentId);
          return next;
        });
      }
    },
  });

  const rescheduleMutation = useMutation({
    mutationFn: rescheduleAppointment,
    onMutate: async (variables) => {
      const startTime = variables.startTime;
      const endTime = variables.endTime;
      const appointmentId = variables.appointmentId;

      await Promise.all([
        queryClient.cancelQueries({ queryKey: listQueryKey }),
        queryClient.cancelQueries({ queryKey: calendarQueryKey }),
      ]);

      const previousList = queryClient.getQueryData<Appointment[] | undefined>(listQueryKey);
      const previousCalendar = queryClient.getQueryData<Appointment[] | undefined>(calendarQueryKey);

      queryClient.setQueryData<Appointment[] | undefined>(listQueryKey, (current) => {
        if (!current) return current;
        return current.map((item) =>
          item.id === appointmentId ? { ...item, startTime, endTime } : item,
        );
      });
      queryClient.setQueryData<Appointment[] | undefined>(calendarQueryKey, (current) => {
        if (!current) return current;
        return current.map((item) =>
          item.id === appointmentId ? { ...item, startTime, endTime } : item,
        );
      });

      return { previousList, previousCalendar };
    },
    onSuccess: ({ appointment }) => {
      upsertAppointment(appointment);
      showToast({
        title: "Appointment updated",
        description: "The appointment has been rescheduled.",
        variant: "success",
      });
    },
    onError: (error, _variables, context) => {
      queryClient.setQueryData(listQueryKey, context?.previousList);
      queryClient.setQueryData(calendarQueryKey, context?.previousCalendar);
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message)
          : "Unable to reschedule appointment.";
      showToast({
        title: "Reschedule failed",
        description: message,
        variant: "destructive",
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: calendarQueryKey });
    },
  });

  const staffBookingMutation = useMutation({
    mutationFn: async (values: StaffBookingValues) => {
      const appointment = await createAppointment({
        title: values.title,
        startTime: toIso(values.startTime),
        endTime: toIso(values.endTime),
        vehicleId: values.vehicleId || undefined,
        technicianId: values.technicianId || undefined,
        reason: values.reason || undefined,
      });

      if (values.technicianId || values.bayId) {
        const assignment = await updateAppointmentAssignment({
          appointmentId: appointment.id,
          technicianId: values.technicianId || undefined,
          bayId: values.bayId || undefined,
        });
        return assignment.appointment;
      }

      return appointment;
    },
    onSuccess: (appointment) => {
      upsertAppointment(appointment);
      showToast({
        title: "Appointment created",
        description: "The appointment has been scheduled.",
        variant: "success",
      });
    },
    onError: (error) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message)
          : "Unable to create appointment.";
      showToast({
        title: "Creation failed",
        description: message,
        variant: "destructive",
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: calendarQueryKey });
    },
  });

  const publicBookingMutation = useMutation({
    mutationFn: async (values: PublicBookingValues) => {
      const appointment = await bookAppointment({
        title: values.title,
        customerId: values.customerId,
        vehicleId: values.vehicleId,
        startTime: toIso(values.startTime),
        endTime: toIso(values.endTime),
        reason: values.reason,
      });

      if (values.technicianId || values.bayId) {
        const assignment = await updateAppointmentAssignment({
          appointmentId: appointment.id,
          technicianId: values.technicianId || undefined,
          bayId: values.bayId || undefined,
        });
        return assignment.appointment;
      }

      return appointment;
    },
    onSuccess: (appointment) => {
      upsertAppointment(appointment);
      showToast({
        title: "Public booking captured",
        description: "The customer has been added to the schedule.",
        variant: "success",
      });
    },
    onError: (error) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message)
          : "Unable to capture booking.";
      showToast({
        title: "Booking failed",
        description: message,
        variant: "destructive",
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: calendarQueryKey });
    },
  });

  const autoScheduleMutation = useMutation({
    mutationFn: autoScheduleAppointment,
    onSuccess: (result) => {
      const appointment = result.appointment;
      upsertAppointment(appointment);
      setAutoVehicleId("");
      setAutoDuration(60);
      showToast({
        title: "Auto-scheduled",
        description: "The best available technician and bay were selected automatically.",
        variant: "success",
      });
    },
    onError: (error) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message)
          : "Unable to auto-schedule.";
      showToast({
        title: "Auto-schedule failed",
        description: message,
        variant: "destructive",
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: calendarQueryKey });
    },
  });

  useAppointmentsSocket((event) => {
    if (event.type === "created" || event.type === "updated") {
      upsertAppointment(event.appointment);
    } else if (event.type === "deleted") {
      removeAppointment(event.appointmentId);
    }
  });

  const filteredAppointments = useMemo(() => {
    const source = appointmentsQuery.data ?? [];
    return source.filter((appointment) => {
      const matchesTechnician =
        !selectedTechnician || appointment.technicianId === selectedTechnician;
      const matchesDay = format(new Date(appointment.startTime), "yyyy-MM-dd") === dayFilter;
      return matchesTechnician && matchesDay;
    });
  }, [appointmentsQuery.data, selectedTechnician, dayFilter]);

  const handleStaffSubmit = (values: StaffBookingValues) => staffBookingMutation.mutateAsync(values);
  const handlePublicSubmit = (values: PublicBookingValues) => publicBookingMutation.mutateAsync(values);

  const handleReschedule = (appointmentId: string, start: Date, end: Date) =>
    rescheduleMutation.mutateAsync({
      appointmentId,
      startTime: start.toISOString(),
      endTime: end.toISOString(),
    });

  const handleAutoSchedule = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!autoVehicleId) {
      showToast({
        title: "Vehicle required",
        description: "Enter a vehicle ID before running auto-schedule.",
        variant: "warning",
      });
      return;
    }
    autoScheduleMutation.mutate({ vehicleId: autoVehicleId, durationMinutes: autoDuration });
  };

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold text-foreground">Schedule workspace</h1>
        <p className="text-sm text-muted-foreground">
          Manage bookings, coordinate technicians, and keep the shop calendar in sync without leaving this view.
        </p>
      </header>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,2fr)]">
        <div className="space-y-6">
          <BookingForms
            technicians={techniciansQuery.data ?? []}
            bays={baysQuery.data ?? []}
            onStaffSubmit={handleStaffSubmit}
            onPublicSubmit={handlePublicSubmit}
            staffPending={staffBookingMutation.isPending}
            publicPending={publicBookingMutation.isPending}
          />

          <form
            onSubmit={handleAutoSchedule}
            className="space-y-4 rounded-lg border border-border/60 bg-card p-4 shadow-sm"
          >
            <header className="space-y-1">
              <h2 className="text-lg font-semibold text-foreground">Auto-schedule next slot</h2>
              <p className="text-sm text-muted-foreground">
                Quickly assign the next available technician and bay based on current workloads.
              </p>
            </header>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1 text-sm">
                <span className="font-medium text-foreground">Vehicle ID</span>
                <input
                  type="text"
                  value={autoVehicleId}
                  onChange={(event) => setAutoVehicleId(event.target.value)}
                  className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  placeholder="VH-1001"
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="font-medium text-foreground">Duration (minutes)</span>
                <input
                  type="number"
                  min={15}
                  step={15}
                  value={autoDuration}
                  onChange={(event) => setAutoDuration(Number(event.target.value) || 60)}
                  className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
                />
              </label>
            </div>
            <div className="flex items-center justify-end gap-2">
              <button
                type="submit"
                disabled={autoScheduleMutation.isPending}
                className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {autoScheduleMutation.isPending ? "Finding slot…" : "Auto-schedule"}
              </button>
            </div>
          </form>
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border border-border/60 bg-card p-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-4">
              <label className="flex flex-col text-sm">
                <span className="font-medium text-foreground">Technician filter</span>
                <select
                  className="rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
                  value={selectedTechnician}
                  onChange={(event) => setSelectedTechnician(event.target.value)}
                >
                  <option value="">All technicians</option>
                  {(techniciansQuery.data ?? []).map((tech) => (
                    <option key={tech.id} value={tech.id}>
                      {tech.email ?? tech.id}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col text-sm">
                <span className="font-medium text-foreground">Day</span>
                <input
                  type="date"
                  className="rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
                  value={dayFilter}
                  onChange={(event) => {
                    const value = event.target.value;
                    setSelectedDate(value ? new Date(value) : new Date());
                  }}
                />
              </label>
              <button
                type="button"
                onClick={() => calendarQuery.refetch()}
                className="ml-auto inline-flex items-center justify-center rounded-md border border-border/70 px-3 py-2 text-sm font-medium text-foreground shadow-sm transition hover:bg-muted"
              >
                Refresh calendar
              </button>
            </div>
          </div>

          <ScheduleCalendar
            appointments={calendarQuery.data ?? []}
            currentDate={selectedDate}
            onDateChange={setSelectedDate}
            onReschedule={handleReschedule}
            isLoading={calendarQuery.isFetching || rescheduleMutation.isPending}
          />
        </div>
      </section>

      <AppointmentsTable
        appointments={filteredAppointments}
        isLoading={appointmentsQuery.isLoading}
        remindersInFlight={remindersInFlight}
        syncInFlight={syncInFlight}
        onSendReminder={(id) => reminderMutation.mutate(id)}
        onSync={(id) => syncMutation.mutate(id)}
      />
    </div>
  );
}
