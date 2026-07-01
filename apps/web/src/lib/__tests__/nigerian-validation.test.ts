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
  it("accepts an official 2-letter state code, 2-digit year, batch letter, and up to 6 serial digits", () => {
    expect(validateNyscStateCode("NYSC/AB/23A/0123")).toEqual({
      normalizedValue: "NYSC/AB/23A/0123",
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
        "NYSC State Code must match the format NYSC/AB/23A/0123. (where AB='state code' e.g AB=Abia; 23A='batch and stream' e.g. 2023 Batch A; 0123='serial number')",
    });
  });
});
