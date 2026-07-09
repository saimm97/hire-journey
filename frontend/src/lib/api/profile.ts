import { ApiError, apiClient } from "@/lib/api/client"
import type {
  Profile,
  ProfileSnapshot,
  ProfileUpdate,
  Project,
  ProjectInput,
} from "@/lib/api/types"

/** Profile onboarding calls. UI never talks to the backend directly — only through here. */
export const profileApi = {
  /** The onboarding snapshot, or null when the user has no profile yet (404). */
  async get(): Promise<ProfileSnapshot | null> {
    try {
      return await apiClient.get<ProfileSnapshot>("/profile")
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null
      throw error
    }
  },

  /** Upload a CV; the backend parses it and returns the populated snapshot. */
  uploadCv(file: File): Promise<ProfileSnapshot> {
    const form = new FormData()
    form.append("file", file)
    return apiClient.postForm<ProfileSnapshot>("/profile/cv", form)
  },

  /** Upload a projects PDF; reuses the CV parser and returns the parsed projects. */
  uploadProjects(file: File): Promise<Project[]> {
    const form = new FormData()
    form.append("file", file)
    return apiClient
      .postForm<{ projects: Project[] }>("/profile/projects/upload", form)
      .then((result) => result.projects)
  },

  /** Persist edited identity + skills, returning the updated profile. */
  update(patch: ProfileUpdate): Promise<Profile> {
    return apiClient.patch<Profile>("/profile", patch)
  },

  /** Replace the CV-sourced projects with the edited set. */
  replaceProjects(projects: ProjectInput[]): Promise<Project[]> {
    return apiClient.put<Project[]>("/profile/projects", projects)
  },
}
