import { describe, expect, it } from "vitest";

import {
  validateNyscStateCode,
  validateUniversityMatriculationNumber,
} from "@/lib/nigerian-validation";

describe("validateUniversityMatriculationNumber", () => {
  it("accepts valid university matriculation numbers", () => {
    expect(validateUniversityMatriculationNumber("csc/2019/1234")).toEqual({
      normalizedValue: "CSC/2019/1234",
      error: null,
    });
    expect(validateUniversityMatriculationNumber("ENG1702456")).toEqual({
      normalizedValue: "ENG1702456",
      error: null,
    });
  });

  it("rejects matriculation numbers outside the allowed format", () => {
    expect(validateUniversityMatriculationNumber("ENG17")).toEqual({
      normalizedValue: "ENG17",
      error:
        'University Matriculation Number must be 8 to 16 characters using only letters, numbers, and "/".',
    });
    expect(validateUniversityMatriculationNumber("LASU-2017-09876")).toEqual({
      normalizedValue: "LASU-2017-09876",
      error:
        'University Matriculation Number must be 8 to 16 characters using only letters, numbers, and "/".',
    });
  });
});

describe("validateNyscStateCode", () => {
  it("accepts any 2-letter code, 2-digit year, A-C batch letter, and 5 to 6 serial digits", () => {
    expect(validateNyscStateCode("NYSC/LG/26B/72673")).toEqual({
      normalizedValue: "NYSC/LG/26B/72673",
      error: null,
    });
    expect(validateNyscStateCode("nysc/la/24c/123456")).toEqual({
      normalizedValue: "NYSC/LA/24C/123456",
      error: null,
    });
  });

  it("rejects values that do not match the expected state code structure", () => {
    expect(validateNyscStateCode("NYSC/LAG/2027/1234")).toEqual({
      normalizedValue: "NYSC/LAG/2027/1234",
      error:
        "NYSC State Code must match the format NYSC/LG/26B/72673.",
    });
  });
});
