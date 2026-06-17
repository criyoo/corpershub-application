function toUniversityList(value: string) {
  return Array.from(
    new Set(
      value
        .trim()
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean)
    )
  ).sort((left, right) => left.localeCompare(right));
}

// Sourced from https://thescholaryweb.com/list-of-universities-in-nigeria/ on 2026-03-16.
const FEDERAL_UNIVERSITIES = toUniversityList(`
Abubakar Tafawa Balewa University Bauchi
Admiralty University Ibusa
Ahmadu Bello University
Air Force Institute of Technology Kaduna
Alex Ekwueme Federal University Ndufu-Alike
Alvan Ikoku Federal University of Education Owerri
Bayero University Kano
David Umahi Federal University of Health Sciences Uburu
Federal University Birnin Kebbi
Federal University Dutsin-Ma
Federal University Dutse
Federal University Gashua
Federal University Gashua
Federal University Gusau
Federal University Kashere
Federal University Lafia
Federal University Lokoja
Federal University Ndifu-Alike
Federal University Oye-Ekiti
Federal University of Agriculture Abeokuta
Federal University of Agriculture Makurdi
Federal University of Education Kano
Federal University of Education Zaria
Federal University of Health Sciences Azare
Federal University of Health Sciences Otukpo
Federal University of Health Technology Ogoni
Federal University of Petroleum Resources Effurun
Federal University of Technology Akure
Federal University of Technology Babura
Federal University of Technology Ikot Abasi
Federal University of Technology Minna
Federal University of Technology Owerri
Federal University Wukari
Michael Okpara University of Agriculture Umudike
Modibbo Adama Federal University of Technology Yola
National Open University of Nigeria
Nigerian Army University Biu
Nigerian Defence Academy Kaduna
Nigerian Maritime University Okerenkoko
Nnamdi Azikiwe University
Obafemi Awolowo University
University of Abuja
University of Agriculture Zuru
University of Benin
University of Calabar
University of Environment and Technology
University of Ibadan
University of Ilorin
University of Jos
University of Lagos
University of Maiduguri
University of Maritime Studies Oron
University of Medical Sciences Teaching Hospital
University of Nigeria Nsukka
University of Port Harcourt
University of Uyo
Usmanu Danfodiyo University Sokoto
`);

const STATE_UNIVERSITIES = toUniversityList(`
AbdulKadir Kure University Minna
Abia State University Uturu
Adamawa State University Mubi
Akwa Ibom State University Ikot Akpaden
Ambrose Alli University
Bauchi State University Gadau
Benue State University Makurdi
Borno State University
Confluence University of Science and Technology Osara
Cross River State University of Technology
David Nweze Umahi University of Medical Sciences
Delta State University Abraka
Delta University of Science and Technology Ozoro
Denis Osadebay University Asaba
Ebonyi State University Abakaliki
Eastern Palm University Ogboko
Edo State University Uzairue
Ekiti State University Ado-Ekiti
Emmanuel Alayande University of Education
First Technical University Ibadan
Gombe State University
Gombe State University of Science and Technology
Ibrahim Badamasi Babangida University Lapai
Ignatius Ajuru University of Education
Imo State University Owerri
Kaduna State University
Kano University of Science and Technology Wudil
Kebbi State University of Science and Technology
Kebbi State University of Science and Technology Aliero
Kingsley Ozumba Mbadiwe University Ogboko
Kogi State University Anyigba
Kwara State University Malete
Ladoke Akintola University of Technology
Lagos State University
Maranatha University
Moshood Abiola University of Science and Technology Abeokuta
Niger Delta University Yenagoa
Ogun State University of Technology Igbesa
Olabisi Onabanjo University Ago-Iwoye
Ondo State Medical University
Ondo State University of Science and Technology Okitipupa
Osun State University Osogbo
Oyo State Technical University
Plateau State University Bokkos
Rivers State University
Sa'adu Zungur University
Shehu Shagari University of Education Sokoto
State University of Medical and Applied Sciences
Sule Lamido University Kafin Hausa
Tai Solarin University of Education Ijagun
Taraba State University Jalingo
Umaru Musa Yar'adua University Katsina
University of Africa Toru-Orua
University of Delta Agbor
Yobe State University Damaturu
Yusuf Maitama Sule University Kano
Zamfara State University
`);

const PRIVATE_UNIVERSITIES = toUniversityList(`
Adeleke University Ede
Afe Babalola University Ado-Ekiti
Ahman Pategi University Pategi
Ajayi Crowther University Oyo
Al-Hikmah University Ilorin
Al-Istiqama University Sumaila
American University of Nigeria Yola
Atiba University Oyo
Augustine University Ilara-Epe
Babcock University Ilishan-Remo
Bakassi Technical University
Baze University Abuja
Bells University of Technology Ota
Benson Idahosa University Benin City
Bowen University Iwo
Caleb University Imota
Capital City University Kano
Caritas University Enugu
Chrisland University Abeokuta
Christopher University Mowe
Claretian University Nekede
Covenant University Ota
Crawford University Igbesa
Crescent University Abeokuta
Crown Hill University Eiyenkorin
Dominican University Ibadan
Edo University Iyamho
Edwin Clark University Kiagbodo
Elizade University Ilara-Mokin
European University of Nigeria Duboyi
Evangel University Akaeze
Fountain University Osogbo
Godfrey Okoye University Ugwuomu-Nike
Gregory University Uturu
Hallmark University Ijebu-Itele
Hezekiah University Umudi
James Hope University Lagos
Joseph Ayo Babalola University Ikeji-Arakeji
Karl-Kumm University Vom
Khadija University Majia
Kings University Ode Omu
KolaDaisi University Ibadan
Landmark University Omu-Aran
Lead City University Ibadan
Legacy University Okija
Madonna University Okija
Maranatha University Lagos
McPherson University Seriki Sotayo
Mewar International University Abuja
Michael and Cecilia Ibru University Owhrode
Mountain Top University Makogi Oba
Nile University Abuja
Novena University Ogume
Obong University Obong Ntak
Oduduwa University Ipetumodu
Pan-Atlantic University Lagos
Paul University Awka
PAMO University of Medical Sciences Port Harcourt
Peaceland University Enugu
Philomath University Kuje Abuja
Precious Cornerstone University Ibadan
Redeemer's University Ede
Renaissance University Ugbawka
Rhema University Aba
Ritman University Ikot Ekpene
Salem University Lokoja
Skyline University Nigeria Kano
Southwestern University Okun Owa
Spiritan University Nneochi
Summit University Offa
Tansian University Umunya
Thomas Adewumi University Oko-Irese
Topfaith University Mkpatak
Trinity University Yaba
University of Mkar Mkar
Veritas University Abuja
Wellspring University Benin City
Wesley University Ondo
Western Delta University Oghara
Westland University Iwo
Anchor University Lagos
Arthur Jarvis University Akpabuyo
Ave Maria University Piyanko
Clifford University Owerrinta
Coal City University Enugu
Crown-Hill University Eiyenkorin Kwara State
Dominion University Ibadan
Eko University of Medical and Health Sciences
Greenfield University Kaduna
Maranatha University Mgbidi
Mudiame University Irrua
Northwest University Sokoto
Palmview University Ijebu-Ode
Dominican University Samonda Ibadan
West Midlands Open University Lagos
Khadija University Majia Jigawa State
Nigerian British University Asa
Peter University Achina
Prince Abubakar Audu University Anyigba
Rayhaan University Kebbi State
Mohammed Kamalud-deen University
Sam Maris University Supare
African University of Science and Technology Abuja
Bells University of Technology Ota
Caleb University Lagos
Crescent University Abeokuta
Glorious Vision University Ogwa
Nile University of Nigeria Abuja
Pan-African University Lagos
Ritman University Ikot Ekpene
The Technical University Ibadan
Wellspring University Benin
Margaret Lawrence University Abuja
University of Fortune Igbotako
Akwa Ibom State University Obio Akpa
Anan University Kwall
Bingham University Karu
Maduka University Enugu
Miva Open University Abuja
Wigwe University Isiokpo
Havilla University Nde-Ikom
University on the Niger Umunya
Lux Mundi University Umuahia
Saaisa University of Medical Sciences and Technology Sokoto
Amadeus University Amizi
Georgian University Kuje
Prime University Kuje
Yenepoya University Ugheli
Arise University of Medical Sciences
The Duke Medical University Calabar
PEN Resource University Gombe
Al-Ansar University Maiduguri
Muhammad Buhari University of Transportation Daura
Saint Mary Polytechnic and University Oku Iboku
Newgate University Minna
European School of Economics and Management
Western Atlantic University Lagos
Isa Mustapha Agwai I Polytechnic and University
Eagle University Iyin Ekiti
Hensard University Toru-Orua
The University of Offa Kwara State
Minaret University Ikirun
One Accord University Mowe
Iconic Open University Sokoto
Nok University Kachia Kaduna State
Nigerian University of Technology and Management Apapa
Federal Polytechnic and University Shendam
Gerar University of Medical Sciences Imope Ijebu
El-Amin University Minna
Amadeus University Amizi Nbawsi
Saisa University of Medical Sciences and Technology Sokoto
Mudiame University Irrua Edo State
The New Gates University Minna
University of Fortune Igbotako Ondo State
Westland University Iwo Osun State
Shanahan University Onitsha
Lux Mundi University Umuahia Abia State
Saint Mary's University of Medical Sciences and Technology
Anthonia University Agbani
Thomas Adewumi University Oko Kwara State
Margaret Lawrence University Galilee
Niger Delta University Wilberforce Island Bayelsa State
`);

export const NIGERIAN_UNIVERSITY_GROUPS = [
  { label: "Federal Universities", universities: FEDERAL_UNIVERSITIES },
  { label: "State Universities", universities: STATE_UNIVERSITIES },
  { label: "Private Universities", universities: PRIVATE_UNIVERSITIES },
];

export const NIGERIAN_UNIVERSITIES = Array.from(
  new Set(NIGERIAN_UNIVERSITY_GROUPS.flatMap((group) => group.universities))
).sort((left, right) => left.localeCompare(right));

const NIGERIAN_UNIVERSITIES_SET = new Set(NIGERIAN_UNIVERSITIES);

export function isNigerianUniversity(value: string) {
  return NIGERIAN_UNIVERSITIES_SET.has(value.trim());
}
