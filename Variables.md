# Variables

## Vendor ID
A code indicating the TPEP provider that provided the record

- TPEP = Technology Passenger Enhancements Project, it can be found defined at the bottom of the first page [TPEP](Documents/tpep_security_standards_promulgated.pdf)
- TLC = Taxi and Limousine Commission, it can found defined at the top of the first page [TLC](Documents/tpep_security_standards_promulgated.pdf)

### Examples
- 1 = Creative Mobile Technologies,LLC
- 2 = Curb Mobility, LLC
- 6 = Myle Technologies
- 7 = Helix


## tpep_pickup_datetime

The date and time when the meter was engaged

## tpep_dropoff_datetime

The date and time when the meter was disengaged

## passenger_count

The number of passengers in the vehicle

## trip_distance

The elapsed trip distance in miles reported by the taximeter

## RatecodeID

The final rate code in effect at the end of the trip.
1 = Standard rate: Standard city rate. Metered billing, starting at $2.50, plus a per-mile/per-minute charge, and possibly additional surcharges for peak hours, nighttime, congestion, etc..

2 = JFK: JFK Airport rate. Mainly for trips between Manhattan and JFK, historically a flat rate (currently $70), plus surcharges such as MTA tax.

3 = Newark: Newark Airport rate. Metered billing, but includes an additional $17.50 Newark surcharge (because Newark is outside New York State), plus round-trip tolls.

4 = Nassau or Westchester: Out-of-city rate to Nassau or Westchester. This is not a simple flat rate; the calculation is complex: the portion within the city limits is charged at the standard meter rate, and the portion outside the city limits is charged at double the meter rate, plus round-trip tolls.

5 = Negotiated fare: Negotiated fare. For trips to destinations outside the city (such as Suffolk County), the driver and passenger negotiate a flat rate before departure, plus MTA tax.

6 = Group ride: Group ride rate. Only applicable to specific Group Ride pickup points (such as Port Authority) to specific destinations (such as 59th Street), with a flat rate per person (such as $3 or $6), during weekday morning peak hours.

99 = Null/unknown: Unknown or null value.

This information comes from [TaxiRate](Documents/taxi_rate_information.pdf) and [TaxiFare](Documents/TaxiFare-TLC.pdf)

## store_and_fwd_flag

This flag indicates whether the trip record was held in vehicle memory before
sending to the vendor, aka “store and forward,” because the vehicle did not
have a connection to the server.
Y = store and forward trip
N = not a store and forward trip

## Location ID
Here is a full map of the different zones in New York *Ai Generated*


- Zone 264 is the "Unknown"
- Zone 265 is the "Outside of NYC"

### PULocationID
TLC Taxi Zone in which the taximeter was engaged

### DOLocationID
TLC Taxi Zone in which the taximeter was disengaged

## payment_type

A numeric code signifying how the passenger paid for the trip.
0 = Flex Fare trip
1 = Credit card
2 = Cash
3 = No charge
4 = Dispute
5 = Unknown
6 = Voided trip

## fare_amount

The time-and-distance fare calculated by the meter. For additional
information on the following columns, see
https://www.nyc.gov/site/tlc/passengers/taxi-fare.page

## extra

Miscellaneous extras and surcharges

## mta_tax

Tax that is automatically triggered based on the metered rate in use

## tip_amount

Tip amount – This field is automatically populated for credit card tips. Cash
tips are not included.

## tolls_amount

Total amount of all tolls paid in trip

## improvement_surcharge

Improvement surcharge assessed trips at the flag drop. The improvement
surcharge began being levied in 2015

## total_amount

The total amount charged to passengers. Does not include cash tips

## congestion_surcharge

Total amount collected in trip for NYS congestion surcharge

## Airport_fee

For pickup only at LaGuardia and John F. Kennedy Airports

## cbd_congestion_fee

Per-trip charge for MTA's Congestion Relief Zone starting Jan. 5, 2025