"use strict";

const iconvLite = require("iconv-lite");
const supportedNames = require("./supported-names.json");
const labelsToNames = require("./labels-to-names.json");

const supportedNamesSet = new Set(supportedNames);

exports.labelToName = label => {
  label = String(label).trim().toLowerCase();

  return labelsToNames[label] || null;
};

exports.decode = (uint8Array, fallbackEncodingName) => {
  let encoding = fallbackEncodingName;
  if (!exports.isSupported(encoding)) {
    throw new RangeError(`"${encoding}" is not a supported encoding name`);
  }

  const bomEncoding = exports.getBOMEncoding(uint8Array);
  if (bomEncoding !== null) {
    encoding = bomEncoding;
  }

  if (encoding === "x-user-defined") {
    let result = "";
    for (const byte of uint8Array) {
      if (byte <= 0x7f) {
        result += String.fromCodePoint(byte);
      } else {
        result += String.fromCodePoint(0xf780 + byte - 0x80);
      }
    }
    return result;
  }

  return iconvLite.decode(uint8Array, encoding);
};

exports.getBOMEncoding = uint8Array => {
  if (uint8Array[0] === 0xfe && uint8Array[1] === 0xff) {
    return "UTF-16BE";
  } else if (uint8Array[0] === 0xff && uint8Array[1] === 0xfe) {
    return "UTF-16LE";
  } else if (
    uint8Array[0] === 0xef &&
    uint8Array[1] === 0xbb &&
    uint8Array[2] === 0xbf
  ) {
    return "UTF-8";
  }

  return null;
};

exports.isSupported = name => {
  return supportedNamesSet.has(String(name));
};
