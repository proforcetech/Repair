import { get, post, put } from "@/lib/api/client";

export interface Appointment {
  id: string;
  title: string;
  startTime: string;
  endTime: string;
  status?: string | null;
  technicianId?: string | null;
  bayId?: string | null;
  customerId?: string | null;
  vehicleId?: string | null;
  reason?: string | null;
  notes?: string | null;
}

export interface CalendarFilters {
  technicianId?: string;
  day?: string;
}

export interface AppointmentCreateInput {
  title: string;
  startTime: string;
  endTime: string;
  vehicleId?: string;
  technicianId?: string;
  bayId?: string;
  reason?: string;
}

export interface AppointmentBookInput {
  title: string;
  customerId: string;
  vehicleId: string;
  startTime: string;
  endTime: string;
  reason: string;
  technicianId?: string;
  bayId?: string;
}

export interface AutoScheduleRequest {
  vehicleId: string;
  durationMinutes: number;
}

export interface RescheduleInput {
  appointmentId: string;
  startTime: string;
  endTime: string;
}

export interface AssignmentInput {
  appointmentId: string;
  technicianId?: string;
  bayId?: string;
  serviceTruck?: string;
}

export async function fetchAppointments() {
  return get<Appointment[]>("/appointments");
}

export async function fetchCalendarAppointments(filters: CalendarFilters) {
  return get<Appointment[]>("/appointments/calendar", {
    params: {
      technicianId: filters.technicianId || undefined,
      day: filters.day || undefined,
    },
  });
}

export async function createAppointment(data: AppointmentCreateInput) {
  return post<Appointment>("/appointments", {
    title: data.title,
    startTime: data.startTime,
    endTime: data.endTime,
    vehicleId: data.vehicleId,
    technicianId: data.technicianId,
    reason: data.reason,
  });
}

export async function bookAppointment(data: AppointmentBookInput) {
  return post<Appointment>("/appointments/book", {
    title: data.title,
    customerId: data.customerId,
    vehicleId: data.vehicleId,
    startTime: data.startTime,
    endTime: data.endTime,
    reason: data.reason,
  });
}

export async function autoScheduleAppointment(request: AutoScheduleRequest) {
  return post<{ message: string; appointment: Appointment }>(
    "/appointments/auto-schedule",
    request,
  );
}

export async function rescheduleAppointment({
  appointmentId,
  startTime,
  endTime,
}: RescheduleInput) {
  return put<{ message: string; appointment: Appointment }>(
    `/appointments/${appointmentId}/reschedule`,
    { startTime, endTime },
  );
}

export async function updateAppointmentAssignment({
  appointmentId,
  technicianId,
  bayId,
  serviceTruck,
}: AssignmentInput) {
  return put<{ message: string; appointment: Appointment }>(
    `/appointments/${appointmentId}/assignment`,
    {
      technicianId,
      bayId,
      serviceTruck,
    },
  );
}

export async function sendAppointmentReminder(appointmentId: string) {
  return post<{ message: string }>(`/appointments/${appointmentId}/reminders`);
}

export async function syncAppointmentToCalendar(appointmentId: string) {
  return post<{ message: string }>(`/appointments/${appointmentId}/sync`);
}
