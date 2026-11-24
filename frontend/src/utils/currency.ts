import countryToCurrency from "country-to-currency";

export type CountryCode = keyof typeof countryToCurrency;

export interface CountryCurrencyOption {
  countryCode: CountryCode;
  countryName: string;
  currencyCode: string;
  currencyName: string;
}

const regionNames = new Intl.DisplayNames(["en"], { type: "region" });
const currencyNames = new Intl.DisplayNames(["en"], { type: "currency" });

export const COUNTRY_CURRENCY_OPTIONS: CountryCurrencyOption[] = Object.entries(countryToCurrency)
  .map(([countryCode, currencyCode]) => ({
    countryCode: countryCode as CountryCode,
    countryName: regionNames.of(countryCode) ?? countryCode,
    currencyCode,
    currencyName: currencyNames.of(currencyCode) ?? currencyCode,
  }))
  .sort((left, right) => left.countryName.localeCompare(right.countryName));

export function getCountryName(countryCode: CountryCode): string {
  return regionNames.of(countryCode) ?? countryCode;
}
